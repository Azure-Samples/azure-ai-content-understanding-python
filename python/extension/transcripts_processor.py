import os
import json
import warnings
from abc import ABC, abstractmethod

warnings.filterwarnings("ignore")

class TranscriptProcessorBase(ABC):
    def __init__(self, name):
        self.name = name

    @abstractmethod
    def process_transcript(self,  transcript_result):
        pass

    # @abstractmethodS
    def get_phrases(self, *args,  transcript_result):
        pass
    
    # @abstractmethod
    def format_timestamp(self, time):
        pass

class BatchTranscriptionProcessor(TranscriptProcessorBase):
    def __init__(self):
        super().__init__(name="BatchTranscriptionProcessor")

    def get_phrases(self, fast_transcription_result):
        return fast_transcription_result.get("recognizedPhrases", [])
        

    def format_timestamp(self, time):
        ticks_per_ms = 10000
        milliseconds = int(time / ticks_per_ms)
        
        seconds, ms = divmod(milliseconds, 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}.{ms:03}"

    
    def process_transcript(self, fast_transcription_result):
        webvtt_string = ["WEBVTT\n"]

        phrases = self.get_phrases(fast_transcription_result)

        for phrase in phrases:

            start_time = self.format_timestamp(phrase["offsetInTicks"])
            end_time = self.format_timestamp(phrase["durationInTicks"])

            speaker = phrase.get("speaker", "Unknown")
            text = phrase['nBest'][0]['display']
            webvtt_string.append(f"{start_time} --> {end_time}")
            webvtt_string.append(f"<v Speaker {speaker}>{text}")
            webvtt_string.append("")

        return "\n".join(webvtt_string)
    
class FastTranscriptionProcessor(TranscriptProcessorBase):
    def __init__(self):
        super().__init__(name="FastTranscriptionProcessor")

    def get_phrases(self, fast_transcription_result):
        return fast_transcription_result.get("phrases", [])
        
    # convert milliseconds to VTT timestamp format
    def format_timestamp(self, milliseconds):
        seconds, ms = divmod(milliseconds, 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}.{ms:03}"
    
    def process_transcript(self, fast_transcription_result):
        webvtt_string = ["WEBVTT\n"]

        phrases = self.get_phrases(fast_transcription_result)

        for phrase in phrases:
            start_time = self.format_timestamp(phrase["offsetMilliseconds"])
            end_time = self.format_timestamp(phrase["offsetMilliseconds"] + phrase["durationMilliseconds"])
            speaker = phrase.get("speaker", "Unknown")
            text = phrase.get("text")
            webvtt_string.append(f"{start_time} --> {end_time}")
            webvtt_string.append(f"<v Speaker {speaker}>{text}")
            webvtt_string.append("")

        return "\n".join(webvtt_string)
    
class CUTranscriptionProcessor(TranscriptProcessorBase):
    def __init__(self):
        super().__init__(name="CUTranscriptionProcessor")
    
    def process_transcript(self, cu_content_extraction_result):
        return cu_content_extraction_result["result"]["contents"][0]["markdown"]


class TranscriptsProcessor:
    def __init__(self):
        self.transcripts = {
            "batch_transcription": BatchTranscriptionProcessor(),
            "fast_transcription": FastTranscriptionProcessor(),
            "cu_markdown": CUTranscriptionProcessor()
        }
    
    def get_transcriptionProcessor(self, transcripts_type)-> TranscriptProcessorBase:
        processor = self.transcripts.get(transcripts_type)
        if not processor:
            raise ValueError(f"'{transcripts_type}' is invalid")
        return processor
    
    def load_transcription_fromLocal(self, file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            transcription = json.load(f)
        print("Load transcription completed.")
        return transcription
    
    def convertBTtoWebVTT(self, transcripts):
        batchTowebVTTProcessor = self.get_transcriptionProcessor("batch_transcription")
        result = batchTowebVTTProcessor.process_transcript(transcripts)
        print("Batch to WebVTT Conversion completed.")
        return result

    def convertFTtoWebVTT(self, transcripts):
        fastTowebVTTProcessor = self.get_transcriptionProcessor("fast_transcription")
        result = fastTowebVTTProcessor.process_transcript(transcripts)
        print("Fast to WebVTT Conversion completed.")
        return result
    
    def extractCUWebVTT(self, transcripts):
        cuWebVTTProcessor = self.get_transcriptionProcessor("cu_markdown")
        result = cuWebVTTProcessor.process_transcript(transcripts)
        print("CU to WebVTT Conversion completed.")
        return result

    def convert_file(self, file_path):
        converted_text = ''
        converted_text_filepath = ''
        transcripts = self.load_transcription_fromLocal(file_path)
        if "combinedRecognizedPhrases" in transcripts:
            print("Processing a batch transcription file.")
            converted_text = self.convertBTtoWebVTT(transcripts)
            converted_text_filepath = self.save_converted_file(converted_text, file_path)
        elif "combinedPhrases" in transcripts:
            print("processing a fast transcription file.")
            converted_text = self.convertFTtoWebVTT(transcripts)
            converted_text_filepath = self.save_converted_file(converted_text, file_path)
        elif "WEBVTT" in str(transcripts):
            print("processing a CU transcription file.")
            converted_text = self.extractCUWebVTT(transcripts)
            converted_text_filepath = self.save_converted_file(converted_text, file_path)
        else:
            print("No supported conversation transcription found. Skipping conversion.")
            # raise ValueError("An error occurred during the conversion process")
        
        return converted_text, converted_text_filepath
    
    def save_converted_file(self, converted_text, file_path):
        temp_file = os.path.join("..", "data", "transcripts_processor_output", f"{os.path.basename(file_path)}.convertedTowebVTT.txt")
        output_dir = os.path.dirname(temp_file)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
 
        try:
            with open(temp_file, 'w', encoding='utf-8') as file:
                file.write(str(converted_text))
            print(f"Conversion completed. The result has been saved to '{temp_file}'")
            return temp_file
        except Exception as e:
            print(f"An error occurred during the conversion process: {e}")
            return None
        
