import json
import os
from pathlib import Path
import tempfile
import unittest
from PIL import Image
from arcade_agent_desk.media import render_demo

SDK=Path(os.environ.get('ARCADE_OS_ROOT',str(Path(__file__).resolve().parents[3]/'scratch-arcade-os')))

class MediaTests(unittest.TestCase):
    def test_actual_wasm_states_produce_distinct_images_and_an_honestly_labeled_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp).resolve()/'media'
            result=render_demo(SDK,out)
            self.assertFalse(result['device_capture']);self.assertFalse(result['real_jobs'])
            self.assertEqual(set(result['states']),{'WORK','DONE','FAIL','WAIT','CANCEL','LOST'})
            pixels=set()
            for state in result['states']:
                with Image.open(out/(state.lower()+'.png')) as image:
                    self.assertEqual(image.size,(320,240));pixels.add(image.convert('RGB').tobytes())
            self.assertEqual(len(pixels),6)
            with Image.open(out/'replay.gif') as movie:self.assertGreater(movie.n_frames,5)
            meta=json.loads((out/'media.json').read_text())
            self.assertEqual(meta,result);self.assertNotIn('key',meta)
            with self.assertRaises(ValueError):render_demo(SDK,out)
