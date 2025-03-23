#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import asyncio
import os
import sys
from typing import List

from dotenv import load_dotenv
from loguru import logger

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import (
    BotInterruptionFrame, 
    EndFrame,
    Frame,
    LLMMessagesFrame,
    TranscriptionFrame,
    TranscriptionMessage,
    TranscriptionUpdateFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.processors.transcript_processor import TranscriptProcessor
from pipecat.serializers.protobuf import ProtobufFrameSerializer
from pipecat.services.cartesia import CartesiaTTSService
from pipecat.services.deepgram import DeepgramSTTService
from pipecat.services.google import GoogleSTTService
from pipecat.services.playht import PlayHTTTSService
from pipecat.services.google import GoogleTTSService
from pipecat.transcriptions.language import Language
from pipecat.services.openai import OpenAILLMService
from pipecat.transports.network.websocket_server import (
    WebsocketServerParams,
    WebsocketServerTransport,
)

load_dotenv(override=True)

logger.remove(0)
logger.add(sys.stderr, level="DEBUG")


class TranslationProcessor(FrameProcessor):
    """A processor that translates text frames from a source language to a target language."""

    def __init__(self, in_language, out_language):
        """Initialize the TranslationProcessor with source and target languages.

        Args:
            in_language (str): The language of the input text.
            out_language (str): The language to translate the text into.
        """
        super().__init__()
        self._out_language = out_language
        self._in_language = in_language

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """Process a frame and translate text frames.

        Args:
            frame (Frame): The frame to process.
            direction (FrameDirection): The direction of the frame.
        """
        await super().process_frame(frame, direction)

        if isinstance(frame, TranscriptionFrame):
            logger.debug(f"Translating {self._in_language}: {frame.text} to {self._out_language}")
            context = [
                {
                    "role": "system",
                    "content": f"You will be provided with a sentence in {self._in_language}, and your task is to only translate it into {self._out_language}.",
                },
                {"role": "user", "content": frame.text},
            ]
            await self.push_frame(LLMMessagesFrame(context))
        else:
            await self.push_frame(frame)


class TranscriptHandler:
    """Simple handler to demonstrate transcript processing.

    Maintains a list of conversation messages and logs them with timestamps.
    """

    def __init__(self, in_language="English", out_language="Spanish"):
        """Initialize the TranscriptHandler with an empty list of messages."""
        self.messages: List[TranscriptionMessage] = []
        self.in_language = in_language
        self.out_language = out_language

    async def on_transcript_update(
        self, processor: TranscriptProcessor, frame: TranscriptionUpdateFrame
    ):
        """Handle new transcript messages.

        Args:
            processor: The TranscriptProcessor that emitted the update
            frame: TranscriptionUpdateFrame containing new messages
        """
        self.messages.extend(frame.messages)

        # Log the new messages
        logger.info("New transcript messages:")
        for msg in frame.messages:
            timestamp = f"[{msg.timestamp}] " if msg.timestamp else ""
            message = {
                "event": "translation",
                "timestamp": msg.timestamp,
                "role": msg.role,
                "language": self.out_language if msg.role == "assistant" else self.in_language,
                "text": msg.content,
            }
            logger.info(f"{timestamp}{msg.role}: {msg.content}")


class SessionTimeoutHandler:
    """Handles actions to be performed when a session times out.
    Inputs:
    - task: Pipeline task (used to queue frames).
    """

    def __init__(self, task):
        self.task = task
        self.background_tasks = set()

    async def handle_timeout(self, client_address):
        """Handles the timeout event for a session silently."""
        try:
            logger.info(f"Connection timeout for {client_address}")

            # Queue a BotInterruptionFrame to notify the system
            await self.task.queue_frames([BotInterruptionFrame()])

            # Start the process to silently end the call in the background
            end_call_task = asyncio.create_task(self._end_call())
            self.background_tasks.add(end_call_task)
            end_call_task.add_done_callback(self.background_tasks.discard)
        except Exception as e:
            logger.error(f"Error during session timeout handling: {e}")

    async def _end_call(self):
        """Silently ends the session."""
        try:
            # Wait a short period before ending the call
            await asyncio.sleep(3)

            # Queue both BotInterruptionFrame and EndFrame to conclude the session
            await self.task.queue_frames([BotInterruptionFrame(), EndFrame()])

            logger.info("Session ended due to timeout.")
        except Exception as e:
            logger.error(f"Error during call termination: {e}")


async def main():
    # Define source and target languages for translation
    in_language = "Bengali"
    out_language = "English"
    
    transport = WebsocketServerTransport(
        params=WebsocketServerParams(
            serializer=ProtobufFrameSerializer(),
            audio_out_enabled=True,
            add_wav_header=True,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            vad_audio_passthrough=True,
            session_timeout=60 * 3,  # 3 minutes
        ),
        host="localhost",  # Explicitly set the host
        port=8765,        # Explicitly set the port
    )

    llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o")



    # Configure service
    stt = GoogleSTTService(
        credentials_path="creds.json",
        location="eu",
        params=GoogleSTTService.InputParams(
            languages=Language.BN_BD,
            model="latest_long",
            enable_interim_results=True,
            enable_automatic_punctuation=False,
        )
    )

    # Use a Spanish voice for the translator
    tts = GoogleTTSService(
        credentials_path="creds.json",
        voice_id="en-IN-Standard-A",
        params=GoogleTTSService.InputParams(
            language=Language.EN_IN,
            gender="female",
        )
    )

    # Create the translation processor
    tp = TranslationProcessor(in_language=in_language, out_language=out_language)
    
    # Create transcript processor for logging translations
    transcript = TranscriptProcessor()
    transcript_handler = TranscriptHandler(in_language=in_language, out_language=out_language)
    
    # Register event handler for transcript updates
    @transcript.event_handler("on_transcript_update")
    async def on_transcript_update(processor, frame):
        await transcript_handler.on_transcript_update(processor, frame)
    
    # We don't need OpenAILLMContext for translation as we're not maintaining conversation context
    context = OpenAILLMContext()
    context_aggregator = llm.create_context_aggregator(context)

    # Set up the translation pipeline
    pipeline = Pipeline(
        [
            transport.input(),  # Websocket input from client
            stt,                # Speech-To-Text
            transcript.user(),  # User transcripts
            tp,                 # Translation processor
            llm,                # LLM (for translation)
            tts,                # Text-To-Speech
            transport.output(), # Websocket output to client
            transcript.assistant(), # Assistant transcripts
            context_aggregator.assistant(), # We don't need this for translation but keeping for compatibility
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=16000,
            audio_out_sample_rate=16000,
            allow_interruptions=False,  # We don't want to interrupt the translator
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        # Silent connection - no introduction message
        # The translator will only respond when the user speaks
        logger.info(f"Client connected: {client.remote_address}. Waiting silently for user speech.")
        # No tts.say() call to maintain silence

    @transport.event_handler("on_session_timeout")
    async def on_session_timeout(transport, client):
        logger.info(f"Entering in timeout for {client.remote_address}")

        timeout_handler = SessionTimeoutHandler(task)
        await timeout_handler.handle_timeout(client)

    runner = PipelineRunner()
    await runner.run(task)


if __name__ == "__main__":
    asyncio.run(main())
