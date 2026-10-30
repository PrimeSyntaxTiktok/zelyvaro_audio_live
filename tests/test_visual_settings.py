import json
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.request import urlopen
from urllib.error import HTTPError
from PySide6.QtGui import QImage, QColor
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from visual_settings import validated
from live_server import LiveServer
import background


class SettingsTests(unittest.TestCase):
    def test_composition_retains_multiple_effects_and_particles(self):
        item={'id':'user-1','name':'Mon thème','effects':['rings','spectrum'],'particles':['bubbles','stars'],
              'colorA':'#123456','colorB':'#abcdef'}
        config=validated({'effects':item['effects'],'particles':item['particles'],'customThemes':[item]})
        self.assertEqual(config['effects'],item['effects'])
        self.assertEqual(config['customThemes'][0]['particles'],item['particles'])

    def test_overlay_placement_style_and_lock_survive_validation(self):
        overlay={'x':.24,'y':.12,'w':.4,'h':.2,'size':92,'locked':True,
                 'visible':True,'italic':True,'font':'Impact','weight':700,'color':'#12aaff',
                 'mode':'manual','manualArtist':'Zelyvaro','manualTitle':'Mon morceau'}
        config=validated({'overlays':{'name':overlay,'track':overlay,'logo':overlay}})
        self.assertEqual(validated(json.loads(json.dumps(config))),config)
        for item in config['overlays'].values():
            for key,value in overlay.items():
                self.assertEqual(item[key],value)

    def test_invalid_entries_and_extreme_values_are_removed(self):
        config=validated({'effects':['rings','script','rings'],'particles':['unknown'],
                          'density':999999,'sensitivity':float('inf'),'colorA':'javascript:bad'})
        self.assertEqual(config['effects'],['rings'])
        self.assertEqual(config['density'],600)
        self.assertNotIn('colorA',config)
        self.assertNotIn('sensitivity',config)


class BackgroundTests(unittest.TestCase):
    def test_import_is_copied_and_survives_source_removal(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            image=QImage(80,140,QImage.Format.Format_RGB32)
            image.fill(QColor('#ff22aa'))
            source=folder/'ma photo.png'
            self.assertTrue(image.save(str(source)))
            value=background.import_background(source,folder/'profile')
            source.unlink()
            self.assertEqual(value['name'],'ma photo.png')
            self.assertTrue(background.state(folder/'profile')['url'].startswith('data:image/png;base64,'))
            self.assertEqual(background.clear(folder/'profile')['url'],'')


    def test_logo_transparency_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            image=QImage(16,16,QImage.Format.Format_ARGB32)
            image.fill(QColor(255,255,255,0))
            image.setPixelColor(8,8,QColor(255,255,255,255))
            source=folder/'logo.png'
            self.assertTrue(image.save(str(source)))
            background.import_background(source,folder/'profile')
            restored=QImage(str(folder/'profile/background.png'))
            self.assertEqual(restored.pixelColor(0,0).alpha(),0)
            self.assertEqual(restored.pixelColor(8,8).alpha(),255)


class LiveServerTests(unittest.TestCase):
    def test_local_source_requires_key_and_keeps_publishing_without_a_window(self):
        with tempfile.TemporaryDirectory() as directory:
            server=LiveServer(Path(__file__).resolve().parents[1]/'app',directory)
            try:
                with self.assertRaises(HTTPError) as error:
                    urlopen(f'http://127.0.0.1:{server.port}/live',timeout=2)
                self.assertEqual(error.exception.code,403)
                with urlopen(server.url,timeout=2) as response:
                    self.assertIn(b'app.js?key=',response.read())
                server.publish('audio',{'bands':[.5]*128,'signal':True})
                with urlopen(f'http://127.0.0.1:{server.port}/health?key={server.token}',timeout=2) as response:
                    self.assertEqual(json.load(response)['audio_packets'],1)
            finally:
                server.close()
