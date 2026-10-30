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
from live_server import LiveServer, preserve_existing_port
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
    def test_migration_adopts_the_existing_personal_source(self):
        with tempfile.TemporaryDirectory() as directory:
            server=LiveServer(Path(__file__).resolve().parents[1]/'app',directory)
            try:
                port_file=Path(directory)/'stream-port.json'
                port_file.unlink()
                preserve_existing_port(directory)
                self.assertEqual(json.loads(port_file.read_text(encoding='utf8'))['port'],server.port)
            finally:
                server.close()

    def test_personal_links_are_identical_after_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            assets=Path(__file__).resolve().parents[1]/'app'
            server=LiveServer(assets,directory)
            before={mode:server.formatted_url(mode) for mode in ('portrait','landscape')}
            with urlopen(before['portrait'],timeout=2) as response:
                response.read()
            server.close()
            restarted=LiveServer(assets,directory)
            try:
                self.assertEqual(before,{mode:restarted.formatted_url(mode) for mode in before})
            finally:
                restarted.close()

    def test_busy_saved_port_never_changes_personal_links(self):
        with tempfile.TemporaryDirectory() as directory:
            assets=Path(__file__).resolve().parents[1]/'app'
            server=LiveServer(assets,directory)
            identity=(Path(directory)/'stream-port.json').read_bytes()
            try:
                with self.assertRaisesRegex(OSError,'liens sont conservés'):
                    LiveServer(assets,directory)
                self.assertEqual((Path(directory)/'stream-port.json').read_bytes(),identity)
            finally:
                server.close()

    def test_two_sources_never_share_or_steal_a_windows_port(self):
        with tempfile.TemporaryDirectory() as directory:
            assets=Path(__file__).resolve().parents[1]/'app'
            first=LiveServer(assets,Path(directory)/'one')
            second=LiveServer(assets,Path(directory)/'two')
            try:
                self.assertNotEqual(first.port,second.port)
                self.assertNotEqual(first.token,second.token)
                for server in (first,second):
                    with urlopen(server.formatted_url('landscape'),timeout=2) as response:
                        self.assertIn(b'width:1920px',response.read())
            finally:
                first.close()
                second.close()

    def test_explicit_formats_keep_fixed_viewport_and_legacy_links_work(self):
        with tempfile.TemporaryDirectory() as directory:
            server=LiveServer(Path(__file__).resolve().parents[1]/'app',directory)
            try:
                for mode,width,height in [('portrait',1080,1920),('landscape',1920,1080)]:
                    url=server.formatted_url(mode)
                    with urlopen(url,timeout=2) as response:
                        html=response.read().decode('utf8')
                    self.assertIn(f'width:{width}px;height:{height}px',html)
                    self.assertIn('stage=1',html)
                    self.assertIn(f'format={mode}',html)
                    with urlopen(url.split('#')[0]+'&stage=1',timeout=2) as response:
                        self.assertIn(b'visual',response.read())
                with self.assertRaises(ValueError):
                    server.formatted_url('wrong')
                with self.assertRaises(HTTPError) as error:
                    urlopen(f'http://127.0.0.1:{server.port}/live?key={server.token}&format=wrong',timeout=2)
                self.assertEqual(error.exception.code,400)
            finally:
                server.close()

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
