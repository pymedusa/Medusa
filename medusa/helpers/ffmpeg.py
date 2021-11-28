"""FFmpeg wrapper."""

import logging
import subprocess
from os.path import join

from medusa import app
from medusa.logger.adapters.style import CustomBraceAdapter

log = CustomBraceAdapter(logging.getLogger(__name__))
log.logger.addHandler(logging.NullHandler())


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

    def detect_video_complete(self, video_file):
        """Check for the last 60 seconds of a video for corruption."""
        command = [
            self.ffmpeg,
            '-v', 'error',
            '-sseof', '-60',
            '-i', video_file,
            '-f', 'null', '-'
        ]

        ffmpeg = subprocess.Popen(
            command, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
            encoding='utf-8', universal_newlines=False
        )

        _, errors = ffmpeg.communicate()
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
            ffmpeg = subprocess.Popen(
                command, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                encoding='utf-8', universal_newlines=False
            )

            output, err = ffmpeg.communicate()
        except (FileNotFoundError, PermissionError):
            return False
        except Exception as error:
            log.warning('Failed to test for the ffmpeg binary. Error: {error}', {'error': error})
            return False

        return True

    def get_ffmpeg_version(self):
        """Test for the ffmpeg version."""
        if not self.test_ffmpeg_binary():
            return False

        command = [
            self.ffmpeg,
            '-version'
        ]

        try:
            ffmpeg = subprocess.Popen(
                command, stderr=subprocess.PIPE, stdout=subprocess.PIPE,
                encoding='utf-8', universal_newlines=False
            )

            output, _ = ffmpeg.communicate()
        except FileNotFoundError:
            return False

        if output:
            output = output.split(' ')
            # Cut out the version
            return output[2]

        return False
