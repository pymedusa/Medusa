"""FFmpeg wrapper."""

import json
import logging
import subprocess
from os.path import join

from medusa import app
from medusa.logger.adapters.style import CustomBraceAdapter

log = CustomBraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


class FfMpegException(Exception):
    """Base FFMPEG / FFPROBE Exception."""


class FfmpegBinaryException(FfMpegException):
    """FFMPEG Binary exception."""


class FfprobeBinaryException(FfMpegException):
    """FFPROBE Binary exception."""


class FfMpeg(object):
    """Wrapper for running FFmpeg checks on video files."""

    def __init__(self):
        """Ffmpeg constructor."""
        super().__init__()
        self.ffprobe = 'ffprobe'
        self.ffmpeg = 'ffmpeg'
        self.ffmpeg_path = app.FFMPEG_PATH
        if self.ffmpeg_path:
            self.ffprobe = join(self.ffmpeg_path, self.ffprobe)
            self.ffmpeg = join(self.ffmpeg_path, self.ffmpeg)

    def get_video_details(self, video_file):
        """Read media info."""
        command = [
            self.ffprobe,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_streams',
            '-show_error',
            video_file
        ]

        process = subprocess.Popen(
            command, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
            encoding='utf-8',
        )
        output, err = process.communicate()
        output = json.loads(output)
        return output

    def check_for_video_and_audio_streams(self, video_file):
        """Read media info and check for a video and audio stream."""
        video_details = self.get_video_details(video_file)
        video_streams = [item for item in video_details['streams'] if item['codec_type'] == 'video']
        audio_streams = [item for item in video_details['streams'] if item['codec_type'] == 'audio']
        if len(video_streams) > 0 and len(audio_streams) > 0:
            return True

        return False

    def scan_for_errors(self, video_file):
        """Check for the last 60 seconds of a video for corruption."""
        command = [
            self.ffmpeg,
            '-v', 'error',
            '-sseof', '-60',
            '-i', video_file,
            '-f', 'null', '-'
        ]

        process = subprocess.Popen(
            command, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
            encoding='utf-8', universal_newlines=False
        )

        _, errors = process.communicate()
        err = [err.strip() for err in errors.split('\n') if err]
        if(err):
            print(err)
            return {
                'file': video_file,
                'errors': err
            }

        return {
            'file': video_file,
            'errors': False
        }

    def test_ffmpeg_binary(self):
        """Test for ffmpeg binary."""
        command = [
            self.ffmpeg,
            '-version'
        ]

        try:
            process = subprocess.Popen(
                command, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                encoding='utf-8', universal_newlines=False
            )

            process.communicate()
        except (FileNotFoundError, PermissionError) as error:
            raise FfmpegBinaryException(f'Error trying to access binary for {self.ffmpeg}, error: {error}')
        except Exception as error:
            log.warning('Failed to test for the ffmpeg binary. Error: {error}', {'error': error})
            raise FfmpegBinaryException(f'Error trying to access binary for {self.ffmpeg}, error: {error}')

        return True

    def test_ffprobe_binary(self):
        """Test for ffmpeg binary."""
        command = [
            self.ffprobe,
            '-version'
        ]

        try:
            process = subprocess.Popen(
                command, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                encoding='utf-8', universal_newlines=False
            )

            process.communicate()
        except (FileNotFoundError, PermissionError) as error:
            raise FfprobeBinaryException(f'Error trying to access binary for {self.ffmpeg}, error: {error}')
        except Exception as error:
            log.warning('Failed to test for the ffmpeg binary. Error: {error}', {'error': error})
            raise FfprobeBinaryException(f'Error trying to access binary for {self.ffmpeg}, error: {error}')

        return True

    def get_ffmpeg_version(self):
        """Test for the ffmpeg version."""
        command = [
            self.ffmpeg,
            '-version'
        ]

        try:
            self.test_ffmpeg_binary()
            process = subprocess.Popen(
                command, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                encoding='utf-8', universal_newlines=False
            )

            output, _ = process.communicate()
        except FileNotFoundError:
            return False

        if output:
            output = output.split(' ')
            # Cut out the version
            return output[2]

        return False

    def get_ffprobe_version(self):
        """Test for the ffprobe version."""
        command = [
            self.ffprobe,
            '-version'
        ]

        try:
            self.test_ffprobe_binary()
            process = subprocess.Popen(
                command, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                encoding='utf-8', universal_newlines=False
            )

            output, _ = process.communicate()
        except FileNotFoundError:
            return False

        if output:
            output = output.split(' ')
            # Cut out the version
            return output[2]

        return False
