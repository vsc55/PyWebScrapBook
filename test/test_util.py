from unittest import mock
import unittest
import sys
import os
import platform
import subprocess
import shutil
import io
import time
import zipfile
import collections
from datetime import datetime, timezone, timedelta
from webscrapbook import util
from webscrapbook.util import frozendict, zip_tuple_timestamp

root_dir = os.path.abspath(os.path.dirname(__file__))

class TestUtils(unittest.TestCase):
    def setUp(self):
        self.maxDiff = 8192

    def test_frozendict(self):
        dict_ = {'a': 1, 'b': 2, 'c': 3}
        frozendict_ = frozendict(dict_)

        self.assertTrue(isinstance(frozendict_, collections.abc.Hashable))
        self.assertTrue(isinstance(frozendict_, collections.abc.Mapping))
        self.assertFalse(isinstance(frozendict_, collections.abc.MutableMapping))

        self.assertEqual(eval(repr(frozendict_)), frozendict_)
        self.assertRegex(repr(frozendict_), r'^frozendict\([^)]*\)$')

        self.assertTrue(frozendict_ == dict_)
        self.assertIn('a', frozendict_)
        self.assertEqual(set(frozendict_), {'a', 'b', 'c'})
        self.assertEqual(list(reversed(frozendict_)), list(frozendict_)[::-1])

        with self.assertRaises(TypeError):
            frozendict_['a'] = 2
        with self.assertRaises(TypeError):
            del frozendict_['a']

        frozendict2 = frozendict_.copy()
        self.assertEqual(frozendict_, frozendict2)
        self.assertIsNot(frozendict_, frozendict2)

    def test_make_hashable(self):
        self.assertEqual(
            type(util.make_hashable({1, 2, 3})),
            frozenset
            )

        self.assertEqual(
            type(util.make_hashable(['foo', 'bar', 'baz'])),
            tuple
            )

        self.assertEqual(
            type(util.make_hashable({'a': 123, 'b': 456, 'c': 789})),
            frozendict
            )
            
        self.assertEqual(
            set(util.make_hashable([{'a': 123, 'b': 456}, [1, 2, 3]])),
            {(1, 2, 3), frozendict({'a': 123, 'b': 456})}
            )

    def test_datetime_to_id(self):
        # create an ID from UTC time
        self.assertEqual(
            util.datetime_to_id(datetime(2020, 1, 2, 3, 4, 5, 67000, tzinfo=timezone.utc)),
            '20200102030405067')

        # create an ID from corresponding UTC time if datetime is another timezone
        self.assertEqual(
            util.datetime_to_id(datetime(2020, 1, 2, 3, 4, 5, 67000, tzinfo=timezone(timedelta(hours=8)))),
            '20200101190405067')

        # create for now if datetime not provided
        self.assertAlmostEqual(
            util.id_to_datetime(util.datetime_to_id(None)).timestamp(),
            datetime.now(timezone.utc).timestamp(),
            delta=3)

    def test_datetime_to_id_legacy(self):
        # create an ID from local datetime
        self.assertEqual(
            util.datetime_to_id_legacy(datetime(2020, 1, 2, 3, 4, 5, 67000)),
            '20200102030405')

        # create an ID from corresponding local time if datetime is another timezone
        self.assertEqual(
            util.datetime_to_id_legacy(datetime(2020, 1, 2, 3, 4, 5, 67000, tzinfo=timezone.utc)),
            util.datetime_to_id_legacy(datetime(2020, 1, 2, 3, 4, 5, 67000) + datetime.now().astimezone().utcoffset())
            )

        # create for now if datetime not provided
        self.assertAlmostEqual(
            util.id_to_datetime_legacy(util.datetime_to_id_legacy(None)).timestamp(),
            datetime.now().timestamp(),
            delta=3)

    def test_id_to_datetime(self):
        self.assertEqual(util.id_to_datetime('20200102030405067'),
            datetime(2020, 1, 2, 3, 4, 5, 67000, timezone.utc))
        self.assertIsNone(util.id_to_datetime('20200102030405'), None)

    def test_id_to_datetime_legacy(self):
        self.assertEqual(util.id_to_datetime_legacy('20200102030405'),
            datetime(2020, 1, 2, 3, 4, 5))
        self.assertIsNone(util.id_to_datetime_legacy('20200102'), None)

    def test_crop(self):
        self.assertEqual(util.crop('dummy text', 10), 'dummy text')
        self.assertEqual(util.crop('dummy text', 9), 'dummy ...')
        self.assertEqual(util.crop('dummy text', 8), 'dummy...')
        self.assertEqual(util.crop('dummy text', 7), 'dumm...')
        self.assertEqual(util.crop('dummy text', 4), 'd...')
        self.assertEqual(util.crop('dummy text', 3), '...')
        self.assertEqual(util.crop('dummy text', 2), '...')
        self.assertEqual(util.crop('dummy text', 1), '...')
        self.assertEqual(util.crop('dummy text', 0), '...')

        self.assertEqual(util.crop('中文字串𠀀', 5), '中文字串𠀀')
        self.assertEqual(util.crop('中文字串𠀀', 4), '中...')

    def test_fix_codec(self):
        self.assertEqual(util.fix_codec('big5'), 'cp950')
        self.assertEqual(util.fix_codec('BIG5'), 'cp950')
        self.assertEqual(util.fix_codec('UTF-8'), 'UTF-8')

    def test_sniff_bom(self):
        fh = io.BytesIO(b'\xef\xbb\xbf' + '中文'.encode('UTF-8'))
        self.assertEqual(util.sniff_bom(fh), 'UTF-8-SIG')
        self.assertEqual(fh.tell(), 3)

        fh = io.BytesIO(b'\xff\xfe' + '中文'.encode('UTF-16-LE'))
        self.assertEqual(util.sniff_bom(fh), 'UTF-16-LE')
        self.assertEqual(fh.tell(), 2)

        fh = io.BytesIO(b'\xfe\xff' + '中文'.encode('UTF-16-BE'))
        self.assertEqual(util.sniff_bom(fh), 'UTF-16-BE')
        self.assertEqual(fh.tell(), 2)

        fh = io.BytesIO(b'\xff\xfe\x00\x00' + '中文'.encode('UTF-32-LE'))
        self.assertEqual(util.sniff_bom(fh), 'UTF-32-LE')
        self.assertEqual(fh.tell(), 4)

        fh = io.BytesIO(b'\x00\x00\xfe\xff' + '中文'.encode('UTF-32-BE'))
        self.assertEqual(util.sniff_bom(fh), 'UTF-32-BE')
        self.assertEqual(fh.tell(), 4)

        fh = io.BytesIO('中文'.encode('UTF-8'))
        self.assertIsNone(util.sniff_bom(fh))
        self.assertEqual(fh.tell(), 0)

        fh = io.BytesIO('中文'.encode('Big5'))
        self.assertIsNone(util.sniff_bom(fh))
        self.assertEqual(fh.tell(), 0)

    def test_is_nullhost(self):
        self.assertTrue(util.is_nullhost('0.0.0.0'))
        self.assertFalse(util.is_nullhost('127.0.0.1'))
        self.assertFalse(util.is_localhost('192.168.0.1'))
        self.assertTrue(util.is_nullhost('::'))
        self.assertFalse(util.is_nullhost('::1'))
        self.assertTrue(util.is_nullhost('0::0'))
        self.assertTrue(util.is_nullhost('0000::0000'))
        self.assertTrue(util.is_nullhost('0000:0000::0000'))
        self.assertTrue(util.is_nullhost('0:0:0:0:0:0:0:0'))
        self.assertTrue(util.is_nullhost('0000:0000:0000:0000:0000:0000:0000:0000'))
        self.assertFalse(util.is_nullhost('wtf'))

    def test_is_localhost(self):
        self.assertFalse(util.is_localhost('0.0.0.0'))
        self.assertTrue(util.is_localhost('127.0.0.1'))
        self.assertFalse(util.is_localhost('192.168.0.1'))
        self.assertFalse(util.is_localhost('::'))
        self.assertTrue(util.is_localhost('::1'))
        self.assertTrue(util.is_localhost('0:0:0:0:0:0:0:1'))
        self.assertTrue(util.is_localhost('0000:0000:0000:0000:0000:0000:0000:0001'))
        self.assertFalse(util.is_localhost('wtf'))

    def test_get_breadcrumbs(self):
        # directory
        self.assertEqual(list(util.get_breadcrumbs(['/path/to/directory/'])), [
            ('.', '/', '/', False),
            ('path', '/path/', '/', False),
            ('to', '/path/to/', '/', False),
            ('directory', '/path/to/directory/', '/', True)
            ])

        # conflicting directory/file
        self.assertEqual(list(util.get_breadcrumbs(['/path/to/fake.ext!/'])), [
            ('.', '/', '/', False),
            ('path', '/path/', '/', False),
            ('to', '/path/to/', '/', False),
            ('fake.ext!', '/path/to/fake.ext!/', '/', True),
            ])

        # sub-archive path(s)
        self.assertEqual(list(util.get_breadcrumbs(['/path/to/archive.ext', ''])), [
            ('.', '/', '/', False),
            ('path', '/path/', '/', False),
            ('to', '/path/to/', '/', False),
            ('archive.ext', '/path/to/archive.ext!/', '!/', True),
            ])

        self.assertEqual(list(util.get_breadcrumbs(['/path/to/archive.ext', 'subdir'])), [
            ('.', '/', '/', False),
            ('path', '/path/', '/', False),
            ('to', '/path/to/', '/', False),
            ('archive.ext', '/path/to/archive.ext!/', '!/', False),
            ('subdir', '/path/to/archive.ext!/subdir/', '/', True),
            ])

        self.assertEqual(list(util.get_breadcrumbs(['/path/to/archive.ext', 'nested1.zip', ''])), [
            ('.', '/', '/', False),
            ('path', '/path/', '/', False),
            ('to', '/path/to/', '/', False),
            ('archive.ext', '/path/to/archive.ext!/', '!/', False),
            ('nested1.zip', '/path/to/archive.ext!/nested1.zip!/', '!/', True),
            ])

        self.assertEqual(list(util.get_breadcrumbs(['/path/to/archive.ext', 'nested1.zip', 'subdir'])), [
            ('.', '/', '/', False),
            ('path', '/path/', '/', False),
            ('to', '/path/to/', '/', False),
            ('archive.ext', '/path/to/archive.ext!/', '!/', False),
            ('nested1.zip', '/path/to/archive.ext!/nested1.zip!/', '!/', False),
            ('subdir', '/path/to/archive.ext!/nested1.zip!/subdir/', '/', True),
            ])

        self.assertEqual(list(util.get_breadcrumbs(['/path/to/archive.ext', 'subdir/nested1.zip', ''])), [
            ('.', '/', '/', False),
            ('path', '/path/', '/', False),
            ('to', '/path/to/', '/', False),
            ('archive.ext', '/path/to/archive.ext!/', '!/', False),
            ('subdir', '/path/to/archive.ext!/subdir/', '/', False),
            ('nested1.zip', '/path/to/archive.ext!/subdir/nested1.zip!/', '!/', True),
            ])

        # base
        self.assertEqual(list(util.get_breadcrumbs(['/path/to/directory/'], base='/wsb')), [
            ('.', '/wsb/', '/', False),
            ('path', '/wsb/path/', '/', False),
            ('to', '/wsb/path/to/', '/', False),
            ('directory', '/wsb/path/to/directory/', '/', True),
            ])

        # base (with slash)
        self.assertEqual(list(util.get_breadcrumbs(['/path/to/directory/'], base='/wsb/')), [
            ('.', '/wsb/', '/', False),
            ('path', '/wsb/path/', '/', False),
            ('to', '/wsb/path/to/', '/', False),
            ('directory', '/wsb/path/to/directory/', '/', True),
            ])

        # topname
        self.assertEqual(list(util.get_breadcrumbs(['/path/to/directory/'], topname='MyWsb')), [
            ('MyWsb', '/', '/', False),
            ('path', '/path/', '/', False),
            ('to', '/path/to/', '/', False),
            ('directory', '/path/to/directory/', '/', True)
            ])


    def test_get_relative_url(self):
        self.assertEqual(
            util.get_relative_url(
                os.path.join(root_dir),
                os.path.join(root_dir, 'tree', 'meta.js'),
                start_is_dir=False,
                ),
            '../',
            )

        self.assertEqual(
            util.get_relative_url(
                os.path.join(root_dir, 'tree', 'icon'),
                os.path.join(root_dir, 'data', '20200101000000000'),
                ),
            '../../tree/icon/',
            )

        self.assertEqual(
            util.get_relative_url(
                os.path.join(root_dir, 'tree', 'icon', 'dummy.png'),
                os.path.join(root_dir, 'data', '20200101000000000'),
                path_is_dir=False,
                ),
            '../../tree/icon/dummy.png',
            )

        self.assertEqual(
            util.get_relative_url(
                os.path.join(root_dir, 'data', '20200102000000000'),
                os.path.join(root_dir, 'data', '20200101000000000'),
                ),
            '../20200102000000000/',
            )

        self.assertEqual(
            util.get_relative_url(
                os.path.join(root_dir, '中文#456.png'),
                os.path.join(root_dir, '中文#123.png'),
                path_is_dir=False,
                start_is_dir=False,
                ),
            '%E4%B8%AD%E6%96%87%23456.png',
            )


    def test_checksum(self):
        self.assertEqual(
            util.checksum(os.path.join(root_dir, 'test_util', 'checksum', 'checksum.txt')),
            'da39a3ee5e6b4b0d3255bfef95601890afd80709'
            )

        self.assertEqual(
            util.checksum(os.path.join(root_dir, 'test_util', 'checksum', 'checksum.txt'), method='sha256'),
            'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
            )

        # file-like
        self.assertEqual(
            util.checksum(io.BytesIO(b''), method='sha256'),
            'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
            )

        self.assertEqual(
            util.checksum(io.BytesIO(b'ABC'), method='sha256'),
            'b5d4045c3f466fa91fe2cc6abe79232a1a57cdf104f7a26e716e0a1e2789df78'
            )

    @unittest.skipUnless(platform.system() == 'Windows', 'requires Windows')
    def test_file_is_link(self):
        # junction
        entry = os.path.join(root_dir, 'test_util', 'file_info', 'junction')

        # capture_output is not supported in Python < 3.8
        subprocess.run([
            'mklink',
            '/j',
            entry,
            os.path.join(root_dir, 'test_util', 'file_info', 'folder'),
            ], shell=True, check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)

        try:
            self.assertTrue(util.file_is_link(entry))
        finally:
            try:
                os.remove(entry)
            except FileNotFoundError:
                pass

        # directory
        entry = os.path.join(root_dir, 'test_util', 'file_info', 'folder')
        self.assertFalse(util.file_is_link(entry))

        # file
        entry = os.path.join(root_dir, 'test_util', 'file_info', 'file.txt')
        self.assertFalse(util.file_is_link(entry))

        # non-exist
        entry = os.path.join(root_dir, 'test_util', 'file_info', 'nonexist')
        self.assertFalse(util.file_is_link(entry))

    def test_file_is_link2(self):
        # symlink
        entry = os.path.join(root_dir, 'test_util', 'file_info', 'symlink')
        try:
            os.symlink(
                os.path.join(root_dir, 'test_util', 'file_info', 'file.txt'),
                entry,
                )
        except OSError:
            if platform.system() == 'Windows':
                self.skipTest('requires administrator or Developer Mode on Windows')
            else:
                raise

        try:
            self.assertTrue(util.file_is_link(entry))
        finally:
            try:
                os.remove(entry)
            except FileNotFoundError:
                pass

    def test_file_info(self):
        entry = os.path.join(root_dir, 'test_util', 'file_info', 'nonexist.file')
        self.assertEqual(
            util.file_info(entry),
            ('nonexist.file', None, None, None)
            )

        entry = os.path.join(root_dir, 'test_util', 'file_info', 'file.txt')
        self.assertEqual(
            util.file_info(entry),
            ('file.txt', 'file', 3, os.stat(entry).st_mtime)
            )

        entry = os.path.join(root_dir, 'test_util', 'file_info', 'folder')
        self.assertEqual(
            util.file_info(entry),
            ('folder', 'dir', None, os.stat(entry).st_mtime)
            )

    @unittest.skipUnless(platform.system() == 'Windows', 'requires Windows')
    def test_file_info_junction(self):
        entry = os.path.join(root_dir, 'test_util', 'file_info', 'junction')

        # target directory
        # capture_output is not supported in Python < 3.8
        subprocess.run([
            'mklink',
            '/j',
            entry,
            os.path.join(root_dir, 'test_util', 'file_info', 'folder'),
            ], shell=True, check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)

        try:
            self.assertEqual(
                util.file_info(entry),
                ('junction', 'link', None, os.lstat(entry).st_mtime)
                )
        finally:
            try:
                os.remove(entry)
            except FileNotFoundError:
                pass

        # target non-exist
        # capture_output is not supported in Python < 3.8
        subprocess.run([
            'mklink',
            '/j',
            entry,
            os.path.join(root_dir, 'test_util', 'file_info', 'nonexist'),
            ], shell=True, check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)

        try:
            self.assertEqual(
                util.file_info(entry),
                ('junction', 'link', None, os.lstat(entry).st_mtime)
                )
        finally:
            try:
                os.remove(entry)
            except FileNotFoundError:
                pass

    def test_file_info_symlink(self):
        entry = os.path.join(root_dir, 'test_util', 'file_info', 'symlink')

        # target file
        try:
            os.symlink(
                os.path.join(root_dir, 'test_util', 'file_info', 'file.txt'),
                entry,
                )
        except OSError:
            if platform.system() == 'Windows':
                self.skipTest('requires administrator or Developer Mode on Windows')
            else:
                raise

        try:
            self.assertEqual(
                util.file_info(entry),
                ('symlink', 'link', None, os.lstat(entry).st_mtime)
                )
        finally:
            try:
                os.remove(entry)
            except FileNotFoundError:
                pass

        # target directory
        try:
            os.symlink(
                os.path.join(root_dir, 'test_util', 'file_info', 'folder'),
                entry,
                )
        except OSError:
            if platform.system() == 'Windows':
                self.skipTest('requires administrator or Developer Mode on Windows')
            else:
                raise

        try:
            self.assertEqual(
                util.file_info(entry),
                ('symlink', 'link', None, os.lstat(entry).st_mtime)
                )
        finally:
            try:
                os.remove(entry)
            except FileNotFoundError:
                pass

        # target non-exist
        try:
            os.symlink(
                os.path.join(root_dir, 'test_util', 'file_info', 'nonexist'),
                entry,
                )
        except OSError:
            if platform.system() == 'Windows':
                self.skipTest('requires administrator or Developer Mode on Windows')
            else:
                raise

        try:
            self.assertEqual(
                util.file_info(entry),
                ('symlink', 'link', None, os.lstat(entry).st_mtime)
                )
        finally:
            try:
                os.remove(entry)
            except FileNotFoundError:
                pass

    def test_listdir(self):
        entry = os.path.join(root_dir, 'test_util', 'listdir')
        self.assertEqual(set(util.listdir(entry)), {
            ('file.txt', 'file', 3, os.stat(os.path.join(entry, 'file.txt')).st_mtime),
            ('folder', 'dir', None, os.stat(os.path.join(entry, 'folder')).st_mtime),
            })
        self.assertEqual(set(util.listdir(entry, recursive=True)), {
            ('file.txt', 'file', 3, os.stat(os.path.join(entry, 'file.txt')).st_mtime),
            ('folder', 'dir', None, os.stat(os.path.join(entry, 'folder')).st_mtime),
            ('folder/.gitkeep', 'file', 0, os.stat(os.path.join(entry, 'folder', '.gitkeep')).st_mtime),
            })

    def test_format_filesize(self):
        self.assertEqual(util.format_filesize(0), '0 B')
        self.assertEqual(util.format_filesize(3), '3 B')
        self.assertEqual(util.format_filesize(1000), '1000 B')
        self.assertEqual(util.format_filesize(1024), '1.0 KB')
        self.assertEqual(util.format_filesize(1080), '1.1 KB')
        self.assertEqual(util.format_filesize(10000), '9.8 KB')
        self.assertEqual(util.format_filesize(10240), '10 KB')
        self.assertEqual(util.format_filesize(20480), '20 KB')
        self.assertEqual(util.format_filesize(1048576), '1.0 MB')
        self.assertEqual(util.format_filesize(2621440), '2.5 MB')
        self.assertEqual(util.format_filesize(10485760), '10 MB')
        self.assertEqual(util.format_filesize(1073741824), '1.0 GB')
        self.assertEqual(util.format_filesize(10737418240), '10 GB')
        self.assertEqual(util.format_filesize(1e14), '91 TB')
        self.assertEqual(util.format_filesize(1e28), '8272 YB')

        self.assertEqual(util.format_filesize(0, si=True), '0 B')
        self.assertEqual(util.format_filesize(3, si=True), '3 B')
        self.assertEqual(util.format_filesize(1000, si=True), '1.0 kB')
        self.assertEqual(util.format_filesize(1024, si=True), '1.0 kB')
        self.assertEqual(util.format_filesize(1080, si=True), '1.1 kB')
        self.assertEqual(util.format_filesize(10000, si=True), '10 kB')
        self.assertEqual(util.format_filesize(10240, si=True), '10 kB')
        self.assertEqual(util.format_filesize(20480, si=True), '20 kB')
        self.assertEqual(util.format_filesize(1048576, si=True), '1.0 MB')
        self.assertEqual(util.format_filesize(2621440, si=True), '2.6 MB')
        self.assertEqual(util.format_filesize(10485760, si=True), '10 MB')
        self.assertEqual(util.format_filesize(1073741824, si=True), '1.1 GB')
        self.assertEqual(util.format_filesize(10737418240, si=True), '11 GB')
        self.assertEqual(util.format_filesize(1e14, si=True), '100 TB')
        self.assertEqual(util.format_filesize(1e28, si=True), '10000 YB')

    def test_is_compressible(self):
        # None
        self.assertFalse(util.is_compressible(None))

        # text/*
        self.assertTrue(util.is_compressible('text/plain'))
        self.assertTrue(util.is_compressible('text/html'))
        self.assertTrue(util.is_compressible('text/css'))
        self.assertTrue(util.is_compressible('text/javascript'))
        self.assertTrue(util.is_compressible('text/markdown'))

        # binary
        self.assertFalse(util.is_compressible('image/jpeg'))
        self.assertFalse(util.is_compressible('application/octet-stream'))
        self.assertFalse(util.is_compressible('application/ogg'))
        self.assertFalse(util.is_compressible('application/pdf'))
        self.assertFalse(util.is_compressible('application/zip'))
        self.assertFalse(util.is_compressible('application/x-rar-compressed'))
        self.assertFalse(util.is_compressible('application/x-gzip'))
        self.assertFalse(util.is_compressible('application/html+zip'))
        self.assertFalse(util.is_compressible('application/x-maff'))

        # text-like application/*
        self.assertTrue(util.is_compressible('application/javascript'))
        self.assertTrue(util.is_compressible('application/ecmascript'))
        self.assertTrue(util.is_compressible('application/x-ecmascript'))
        self.assertTrue(util.is_compressible('application/x-javascript'))
        self.assertTrue(util.is_compressible('application/json'))
        self.assertTrue(util.is_compressible('application/xml'))

        # text-like suffixes
        self.assertTrue(util.is_compressible('application/xhtml+xml'))
        self.assertTrue(util.is_compressible('application/ld+json'))

    def test_mime_is_html(self):
        self.assertTrue(util.mime_is_html('text/html'))
        self.assertTrue(util.mime_is_html('application/xhtml+xml'))
        self.assertFalse(util.mime_is_html('application/html+zip'))
        self.assertFalse(util.mime_is_html('application/x-maff'))
        self.assertFalse(util.mime_is_html('text/plain'))
        self.assertFalse(util.mime_is_html('text/markdown'))
        self.assertFalse(util.mime_is_html('text/xml'))
        self.assertFalse(util.mime_is_html('image/svg+xml'))
        self.assertFalse(util.mime_is_html('application/octet-stream'))

    def test_mime_is_archive(self):
        self.assertFalse(util.mime_is_archive('text/html'))
        self.assertFalse(util.mime_is_archive('application/xhtml+xml'))
        self.assertTrue(util.mime_is_archive('application/html+zip'))
        self.assertTrue(util.mime_is_archive('application/x-maff'))
        self.assertFalse(util.mime_is_archive('text/plain'))
        self.assertFalse(util.mime_is_archive('text/markdown'))
        self.assertFalse(util.mime_is_archive('text/xml'))
        self.assertFalse(util.mime_is_archive('image/svg+xml'))
        self.assertFalse(util.mime_is_archive('application/octet-stream'))

    def test_mime_is_htz(self):
        self.assertFalse(util.mime_is_htz('text/html'))
        self.assertFalse(util.mime_is_htz('application/xhtml+xml'))
        self.assertTrue(util.mime_is_htz('application/html+zip'))
        self.assertFalse(util.mime_is_htz('application/x-maff'))
        self.assertFalse(util.mime_is_htz('text/plain'))
        self.assertFalse(util.mime_is_htz('text/markdown'))
        self.assertFalse(util.mime_is_htz('text/xml'))
        self.assertFalse(util.mime_is_htz('image/svg+xml'))
        self.assertFalse(util.mime_is_htz('application/octet-stream'))

    def test_mime_is_maff(self):
        self.assertFalse(util.mime_is_maff('text/html'))
        self.assertFalse(util.mime_is_maff('application/xhtml+xml'))
        self.assertFalse(util.mime_is_maff('application/html+zip'))
        self.assertTrue(util.mime_is_maff('application/x-maff'))
        self.assertFalse(util.mime_is_maff('text/plain'))
        self.assertFalse(util.mime_is_maff('text/markdown'))
        self.assertFalse(util.mime_is_maff('text/xml'))
        self.assertFalse(util.mime_is_maff('image/svg+xml'))
        self.assertFalse(util.mime_is_maff('application/octet-stream'))

    def test_mime_is_markdown(self):
        self.assertFalse(util.mime_is_markdown('text/html'))
        self.assertFalse(util.mime_is_markdown('application/xhtml+xml'))
        self.assertFalse(util.mime_is_markdown('application/html+zip'))
        self.assertFalse(util.mime_is_markdown('application/x-maff'))
        self.assertFalse(util.mime_is_markdown('text/plain'))
        self.assertTrue(util.mime_is_markdown('text/markdown'))
        self.assertFalse(util.mime_is_markdown('text/xml'))
        self.assertFalse(util.mime_is_markdown('image/svg+xml'))
        self.assertFalse(util.mime_is_markdown('application/octet-stream'))

    def test_is_html(self):
        self.assertTrue(util.is_html('index.html'))
        self.assertTrue(util.is_html('index.xhtml'))
        self.assertFalse(util.is_html('20200101000000000.htz'))
        self.assertFalse(util.is_html('20200101000000000.maff'))
        self.assertFalse(util.is_html('20200101000000000/index.md'))
        self.assertFalse(util.is_html('20200101000000000/test.txt'))
        self.assertFalse(util.is_html('20200101000000000/test.xml'))
        self.assertFalse(util.is_html('20200101000000000/test.svg'))
        self.assertFalse(util.is_html('20200101000000000/whatever'))

    def test_is_archive(self):
        self.assertFalse(util.is_archive('index.html'))
        self.assertFalse(util.is_archive('index.xhtml'))
        self.assertTrue(util.is_archive('20200101000000000.htz'))
        self.assertTrue(util.is_archive('20200101000000000.maff'))
        self.assertFalse(util.is_archive('20200101000000000/index.md'))
        self.assertFalse(util.is_archive('20200101000000000/test.txt'))
        self.assertFalse(util.is_archive('20200101000000000/test.xml'))
        self.assertFalse(util.is_archive('20200101000000000/test.svg'))
        self.assertFalse(util.is_archive('20200101000000000/whatever'))

    def test_is_htz(self):
        self.assertFalse(util.is_htz('index.html'))
        self.assertFalse(util.is_htz('index.xhtml'))
        self.assertTrue(util.is_htz('20200101000000000.htz'))
        self.assertFalse(util.is_htz('20200101000000000.maff'))
        self.assertFalse(util.is_htz('20200101000000000/index.md'))
        self.assertFalse(util.is_htz('20200101000000000/test.txt'))
        self.assertFalse(util.is_htz('20200101000000000/test.xml'))
        self.assertFalse(util.is_htz('20200101000000000/test.svg'))
        self.assertFalse(util.is_htz('20200101000000000/whatever'))

    def test_is_maff(self):
        self.assertFalse(util.is_maff('index.html'))
        self.assertFalse(util.is_maff('index.xhtml'))
        self.assertFalse(util.is_maff('20200101000000000.htz'))
        self.assertTrue(util.is_maff('20200101000000000.maff'))
        self.assertFalse(util.is_maff('20200101000000000/index.md'))
        self.assertFalse(util.is_maff('20200101000000000/test.txt'))
        self.assertFalse(util.is_maff('20200101000000000/test.xml'))
        self.assertFalse(util.is_maff('20200101000000000/test.svg'))
        self.assertFalse(util.is_maff('20200101000000000/whatever'))

    def test_is_markdown(self):
        self.assertFalse(util.is_markdown('index.html'))
        self.assertFalse(util.is_markdown('index.xhtml'))
        self.assertFalse(util.is_markdown('20200101000000000.htz'))
        self.assertFalse(util.is_markdown('20200101000000000.maff'))
        self.assertTrue(util.is_markdown('20200101000000000/index.md'))
        self.assertFalse(util.is_markdown('20200101000000000/test.txt'))
        self.assertFalse(util.is_markdown('20200101000000000/test.xml'))
        self.assertFalse(util.is_markdown('20200101000000000/test.svg'))
        self.assertFalse(util.is_markdown('20200101000000000/whatever'))

    def test_zip_tuple_timestamp(self):
        self.assertEqual(
            util.zip_tuple_timestamp((1987, 1, 1, 0, 0, 0)),
            time.mktime((1987, 1, 1, 0, 0, 0, 0, 0, -1))
            )

    def test_zip_timestamp(self):
        self.assertEqual(
            util.zip_timestamp(zipfile.ZipInfo('dummy', (1987, 1, 1, 0, 0, 0))),
            time.mktime((1987, 1, 1, 0, 0, 0, 0, 0, -1))
            )

    def test_zip_file_info(self):
        zip_filename = os.path.join(root_dir, 'test_util', 'zipfile.zip')
        try:
            with zipfile.ZipFile(zip_filename, 'w') as zh:
                zh.writestr(zipfile.ZipInfo('file.txt', (1987, 1, 1, 0, 0, 0)), '123456')
                zh.writestr(zipfile.ZipInfo('folder/', (1988, 1, 1, 0, 0, 0)), '')
                zh.writestr(zipfile.ZipInfo('folder/.gitkeep', (1989, 1, 1, 0, 0, 0)), '123')
                zh.writestr(zipfile.ZipInfo('implicit_folder/.gitkeep', (1990, 1, 1, 0, 0, 0)), '1234')

            self.assertEqual(
                util.zip_file_info(zip_filename, 'file.txt'),
                ('file.txt', 'file', 6, zip_tuple_timestamp((1987, 1, 1, 0, 0, 0)))
                )

            self.assertEqual(
                util.zip_file_info(zip_filename, 'folder'),
                ('folder', 'dir', None, zip_tuple_timestamp((1988, 1, 1, 0, 0, 0)))
                )

            self.assertEqual(
                util.zip_file_info(zip_filename, 'folder/'),
                ('folder', 'dir', None, zip_tuple_timestamp((1988, 1, 1, 0, 0, 0)))
                )

            self.assertEqual(
                util.zip_file_info(zip_filename, 'folder/.gitkeep'),
                ('.gitkeep', 'file', 3, zip_tuple_timestamp((1989, 1, 1, 0, 0, 0)))
                )

            self.assertEqual(
                util.zip_file_info(zip_filename, 'implicit_folder'),
                ('implicit_folder', None, None, None)
                )

            self.assertEqual(
                util.zip_file_info(zip_filename, 'implicit_folder/'),
                ('implicit_folder', None, None, None)
                )

            self.assertEqual(
                util.zip_file_info(zip_filename, 'implicit_folder', check_implicit_dir=True),
                ('implicit_folder', 'dir', None, None)
                )

            self.assertEqual(
                util.zip_file_info(zip_filename, 'implicit_folder/', check_implicit_dir=True),
                ('implicit_folder', 'dir', None, None)
                )

            self.assertEqual(
                util.zip_file_info(zip_filename, 'implicit_folder/.gitkeep'),
                ('.gitkeep', 'file', 4, zip_tuple_timestamp((1990, 1, 1, 0, 0, 0)))
                )

            self.assertEqual(
                util.zip_file_info(zip_filename, 'nonexist'),
                ('nonexist', None, None, None)
                )

            self.assertEqual(
                util.zip_file_info(zip_filename, 'nonexist/'),
                ('nonexist', None, None, None)
                )

            # take zipfile.ZipFile
            with zipfile.ZipFile(zip_filename, 'r') as zip:
                self.assertEqual(
                    util.zip_file_info(zip, 'file.txt'),
                    ('file.txt', 'file', 6, zip_tuple_timestamp((1987, 1, 1, 0, 0, 0)))
                    )
        finally:
            try:
                os.remove(zip_filename)
            except FileNotFoundError:
                pass

    def test_zip_listdir(self):
        zip_filename = os.path.join(root_dir, 'test_util', 'zipfile.zip')
        try:
            with zipfile.ZipFile(zip_filename, 'w') as zh:
                zh.writestr(zipfile.ZipInfo('file.txt', (1987, 1, 1, 0, 0, 0)), '123456')
                zh.writestr(zipfile.ZipInfo('folder/', (1988, 1, 1, 0, 0, 0)), '')
                zh.writestr(zipfile.ZipInfo('folder/.gitkeep', (1989, 1, 1, 0, 0, 0)), '123')
                zh.writestr(zipfile.ZipInfo('implicit_folder/.gitkeep', (1990, 1, 1, 0, 0, 0)), '1234')

            self.assertEqual(set(util.zip_listdir(zip_filename, '')), {
                ('folder', 'dir', None, zip_tuple_timestamp((1988, 1, 1, 0, 0, 0))),
                ('implicit_folder', 'dir', None, None),
                ('file.txt', 'file', 6, zip_tuple_timestamp((1987, 1, 1, 0, 0, 0))),
                })

            self.assertEqual(set(util.zip_listdir(zip_filename, '/')), {
                ('folder', 'dir', None, zip_tuple_timestamp((1988, 1, 1, 0, 0, 0))),
                ('implicit_folder', 'dir', None, None),
                ('file.txt', 'file', 6, zip_tuple_timestamp((1987, 1, 1, 0, 0, 0))),
                })

            self.assertEqual(set(util.zip_listdir(zip_filename, '', recursive=True)), {
                ('folder', 'dir', None, zip_tuple_timestamp((1988, 1, 1, 0, 0, 0))),
                ('folder/.gitkeep', 'file', 3, zip_tuple_timestamp((1989, 1, 1, 0, 0, 0))),
                ('implicit_folder', 'dir', None, None),
                ('implicit_folder/.gitkeep', 'file', 4, zip_tuple_timestamp((1990, 1, 1, 0, 0, 0))),
                ('file.txt', 'file', 6, zip_tuple_timestamp((1987, 1, 1, 0, 0, 0))),
                })

            self.assertEqual(set(util.zip_listdir(zip_filename, 'folder')), {
                ('.gitkeep', 'file', 3, zip_tuple_timestamp((1989, 1, 1, 0, 0, 0)))
                })

            self.assertEqual(set(util.zip_listdir(zip_filename, 'folder/')), {
                ('.gitkeep', 'file', 3, zip_tuple_timestamp((1989, 1, 1, 0, 0, 0)))
                })

            self.assertEqual(set(util.zip_listdir(zip_filename, 'implicit_folder')), {
                ('.gitkeep', 'file', 4, zip_tuple_timestamp((1990, 1, 1, 0, 0, 0)))
                })

            self.assertEqual(set(util.zip_listdir(zip_filename, 'implicit_folder/')), {
                ('.gitkeep', 'file', 4, zip_tuple_timestamp((1990, 1, 1, 0, 0, 0)))
                })

            with self.assertRaises(util.ZipDirNotFoundError):
                set(util.zip_listdir(zip_filename, 'nonexist'))

            with self.assertRaises(util.ZipDirNotFoundError):
                set(util.zip_listdir(zip_filename, 'nonexist/'))

            with self.assertRaises(util.ZipDirNotFoundError):
                set(util.zip_listdir(zip_filename, 'file.txt'))

            # take zipfile.ZipFile
            with zipfile.ZipFile(zip_filename, 'r') as zip:
                self.assertEqual(set(util.zip_listdir(zip, '')), {
                    ('folder', 'dir', None, zip_tuple_timestamp((1988, 1, 1, 0, 0, 0))),
                    ('implicit_folder', 'dir', None, None),
                    ('file.txt', 'file', 6, zip_tuple_timestamp((1987, 1, 1, 0, 0, 0))),
                    })
        finally:
            try:
                os.remove(zip_filename)
            except FileNotFoundError:
                pass

    def test_zip_hasdir(self):
        zip_filename = os.path.join(root_dir, 'test_util', 'zipfile.zip')
        try:
            with zipfile.ZipFile(zip_filename, 'w') as zh:
                zh.writestr('file.txt', '123456')
                zh.writestr('folder/', '')
                zh.writestr('folder/.gitkeep', '123')
                zh.writestr('implicit_folder/.gitkeep', '1234')

            self.assertTrue(util.zip_hasdir(zip_filename, ''))
            self.assertTrue(util.zip_hasdir(zip_filename, '/'))
            self.assertFalse(util.zip_hasdir(zip_filename, 'file.txt'))
            self.assertFalse(util.zip_hasdir(zip_filename, 'file.txt/'))
            self.assertTrue(util.zip_hasdir(zip_filename, 'folder'))
            self.assertTrue(util.zip_hasdir(zip_filename, 'folder/'))
            self.assertTrue(util.zip_hasdir(zip_filename, 'implicit_folder'))
            self.assertTrue(util.zip_hasdir(zip_filename, 'implicit_folder/'))
            self.assertFalse(util.zip_hasdir(zip_filename, 'implicit_folder/.gitkeep'))
            self.assertFalse(util.zip_hasdir(zip_filename, 'implicit_folder/.gitkeep/'))
        finally:
            try:
                os.remove(zip_filename)
            except FileNotFoundError:
                pass

    def test_parse_content_type(self):
        self.assertEqual(
            util.parse_content_type('text/html; charset=UTF-8'),
            ('text/html', {'charset': 'UTF-8'}),
            )
        self.assertEqual(
            util.parse_content_type('text/html; charset="UTF-8"'),
            ('text/html', {'charset': 'UTF-8'}),
            )
        self.assertEqual(
            util.parse_content_type('TEXT/HTML; CHARSET="UTF-8"'),
            ('text/html', {'charset': 'UTF-8'}),
            )
        self.assertEqual(
            util.parse_content_type(None),
            (None, {}),
            )
        self.assertEqual(
            util.parse_content_type(''),
            (None, {}),
            )

    def test_parse_datauri(self):
        self.assertEqual(
            util.parse_datauri('data:text/plain;base64,QUJDMTIz5Lit5paH'),
            (b'ABC123\xe4\xb8\xad\xe6\x96\x87', 'text/plain', {})
            )
        self.assertEqual(
            util.parse_datauri('data:text/plain,ABC123%E4%B8%AD%E6%96%87'),
            (b'ABC123\xe4\xb8\xad\xe6\x96\x87', 'text/plain', {})
            )
        self.assertEqual(
            util.parse_datauri('data:text/plain;filename=ABC%E6%AA%94.md;base64,QUJDMTIz5Lit5paH'),
            (b'ABC123\xe4\xb8\xad\xe6\x96\x87', 'text/plain', {'filename': 'ABC%E6%AA%94.md'})
            )
        self.assertEqual(
            util.parse_datauri('data:text/plain;filename=ABC%E6%AA%94.md,ABC123%E4%B8%AD%E6%96%87'),
            (b'ABC123\xe4\xb8\xad\xe6\x96\x87', 'text/plain', {'filename': 'ABC%E6%AA%94.md'})
            )
        self.assertEqual(
            util.parse_datauri('data:text/plain;charset=big5;filename=ABC%E6%AA%94.md;base64,QUJDMTIz5Lit5paH'),
            (b'ABC123\xe4\xb8\xad\xe6\x96\x87', 'text/plain', {'filename': 'ABC%E6%AA%94.md', 'charset': 'big5'})
            )
        self.assertEqual(
            util.parse_datauri('data:text/plain;charset=big5;filename=ABC%E6%AA%94.md,ABC123%E4%B8%AD%E6%96%87'),
            (b'ABC123\xe4\xb8\xad\xe6\x96\x87', 'text/plain', {'filename': 'ABC%E6%AA%94.md', 'charset': 'big5'})
            )

        # missing MIME => empty MIME
        self.assertEqual(
            util.parse_datauri('data:,ABC'),
            (b'ABC', '', {})
            )

        # non-ASCII data => treat as UTF-8
        self.assertEqual(
            util.parse_datauri('data:text/plain,ABC中文'),
            (b'ABC\xe4\xb8\xad\xe6\x96\x87', 'text/plain', {})
            )

        # incomplete => raise DataUriMalformedError
        with self.assertRaises(util.DataUriMalformedError):
            util.parse_datauri('data:')
        with self.assertRaises(util.DataUriMalformedError):
            util.parse_datauri('data:text/html')
        with self.assertRaises(util.DataUriMalformedError):
            util.parse_datauri('data:text/html;base64')

        # malformed base64 => raise DataUriMalformedError
        with self.assertRaises(util.DataUriMalformedError):
            util.parse_datauri('data:text/plain;base64,ABC')

    def test_get_charset(self):
        root = os.path.join(root_dir, 'test_util', 'get_charset')
        self.assertIsNone(util.get_charset(os.path.join(root, 'charset1.html')))
        self.assertEqual(util.get_charset(os.path.join(root, 'charset2.html')), 'UTF-8')
        self.assertEqual(util.get_charset(os.path.join(root, 'charset3.html')), 'Big5')
        self.assertEqual(util.get_charset(os.path.join(root, 'charset4.html')), 'UTF-8')
        self.assertEqual(util.get_charset(os.path.join(root, 'charset5.html')), 'BIG5')

    def test_iter_meta_refresh(self):
        root = os.path.join(root_dir, 'test_util', 'iter_meta_refresh')
        self.assertEqual(
            list(util.iter_meta_refresh(os.path.join(root, 'refresh1.html'))),
            [
                (15, 'target.html', None),
                (0, None, None),
                (0, 'target.html', None),
                (0, 'target2.html', None),
                ],
            )
        self.assertEqual(
            list(util.iter_meta_refresh(os.path.join(root, 'refresh2.html'))),
            [
                (15, 'target.html', None),
                (0, 'target.html', None),
                (0, 'target2.html', None),
                ],
            )
        self.assertEqual(
            list(util.iter_meta_refresh(os.path.join(root, 'refresh3.html'))),
            [
                (0, 'target-title.html', ['title']),
                (0, 'target-iframe.html', ['iframe']),
                (0, 'target-noframes.html', ['noframes']),
                (0, 'target-noscript.html', ['noscript']),
                (0, 'target-noembed.html', ['noembed']),
                (0, 'target-textarea.html', ['textarea']),
                (0, 'target-template.html', ['template']),
                (0, 'target-xmp.html', ['xmp']),
                ],
            )
        self.assertEqual(
            list(util.iter_meta_refresh(os.path.join(root, 'refresh4.html'))),
            [(0, 'target.html', ['noscript', 'noframes'])],
            )
        self.assertEqual(
            list(util.iter_meta_refresh(os.path.join(root, 'nonexist.html'))),
            [],
            )

        zip_filename = os.path.join(root_dir, 'test_util', 'zipfile.zip')
        try:
            with zipfile.ZipFile(zip_filename, 'w') as zh:
                zh.writestr('refresh.html', '<meta http-equiv="refresh" content="0;url=target.html">')

            with zipfile.ZipFile(zip_filename, 'r') as zh:
                with zh.open('refresh.html') as fh:
                    self.assertEqual(
                        list(util.iter_meta_refresh(fh)),
                        [(0, 'target.html', None)]
                        )
        finally:
            try:
                os.remove(zip_filename)
            except FileNotFoundError:
                pass

    def test_parse_meta_refresh(self):
        root = os.path.join(root_dir, 'test_util', 'iter_meta_refresh')
        self.assertEqual(
            util.parse_meta_refresh(os.path.join(root, 'refresh1.html')),
            (0, 'target.html', None)
            )
        self.assertEqual(
            util.parse_meta_refresh(os.path.join(root, 'refresh2.html')),
            (0, 'target.html', None)
            )
        self.assertEqual(
            util.parse_meta_refresh(os.path.join(root, 'refresh3.html')),
            (None, None, None)
            )
        self.assertEqual(
            util.parse_meta_refresh(os.path.join(root, 'refresh4.html')),
            (None, None, None)
            )
        self.assertEqual(
            util.parse_meta_refresh(os.path.join(root, 'nonexist.html')),
            (None, None, None)
            )

        zip_filename = os.path.join(root_dir, 'test_util', 'zipfile.zip')
        try:
            with zipfile.ZipFile(zip_filename, 'w') as zh:
                zh.writestr('refresh.html', '<meta http-equiv="refresh" content="0;url=target.html">')

            with zipfile.ZipFile(zip_filename, 'r') as zh:
                with zh.open('refresh.html') as fh:
                    self.assertEqual(
                        util.parse_meta_refresh(fh),
                        (0, 'target.html', None)
                        )
        finally:
            try:
                os.remove(zip_filename)
            except FileNotFoundError:
                pass

    def test_parse_maff_index_rdf(self):
        maff_filename = os.path.join(root_dir, 'test_util', 'tempfile.maff')
        try:
            with zipfile.ZipFile(maff_filename, 'w') as zh:
                zh.writestr(zipfile.ZipInfo('19870101/index.rdf', (1987, 1, 1, 0, 0, 0)), """<?xml version="1.0"?>
<RDF:RDF xmlns:MAF="http://maf.mozdev.org/metadata/rdf#"
         xmlns:NC="http://home.netscape.com/NC-rdf#"
         xmlns:RDF="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <RDF:Description RDF:about="urn:root">
    <MAF:originalurl RDF:resource="http://example.com/"/>
    <MAF:title RDF:resource="Example MAFF"/>
    <MAF:archivetime RDF:resource="Mon, 25 Dec 2017 17:27:46 GMT"/>
    <MAF:indexfilename RDF:resource="index.html"/>
    <MAF:charset RDF:resource="UTF-8"/>
  </RDF:Description>
</RDF:RDF>""")

            with zipfile.ZipFile(maff_filename, 'r') as zh:
                with zh.open('19870101/index.rdf', 'r') as rdf:
                    self.assertEqual(
                        util.parse_maff_index_rdf(rdf),
                        ('Example MAFF', 'http://example.com/', 'Mon, 25 Dec 2017 17:27:46 GMT', 'index.html', 'UTF-8')
                        )
        finally:
            try:
                os.remove(maff_filename)
            except FileNotFoundError:
                pass

    def test_get_maff_pages(self):
        maff_filename = os.path.join(root_dir, 'test_util', 'tempfile.maff')
        try:
            with zipfile.ZipFile(maff_filename, 'w') as zh:
                zh.writestr(zipfile.ZipInfo('webpage1/index.rdf', (1987, 1, 1, 0, 0, 0)), """<?xml version="1.0"?>
<RDF:RDF xmlns:MAF="http://maf.mozdev.org/metadata/rdf#"
         xmlns:NC="http://home.netscape.com/NC-rdf#"
         xmlns:RDF="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <RDF:Description RDF:about="urn:root">
    <MAF:originalurl RDF:resource="http://example.com/"/>
    <MAF:title RDF:resource="Example MAFF"/>
    <MAF:archivetime RDF:resource="Mon, 25 Dec 2017 17:27:46 GMT"/>
    <MAF:indexfilename RDF:resource="index.html"/>
    <MAF:charset RDF:resource="UTF-8"/>
  </RDF:Description>
</RDF:RDF>""")
                zh.writestr(zipfile.ZipInfo('webpage2/index.html', (1987, 1, 1, 0, 0, 0)), '')
                zh.writestr(zipfile.ZipInfo('webpage3/index.svg', (1987, 1, 1, 0, 0, 0)), '')

            self.assertEqual(util.get_maff_pages(maff_filename), [
                ('Example MAFF', 'http://example.com/', 'Mon, 25 Dec 2017 17:27:46 GMT', 'webpage1/index.html', 'UTF-8'),
                (None, None, None, 'webpage2/index.html', None),
                (None, None, None, 'webpage3/index.svg', None),
                ])

            with zipfile.ZipFile(maff_filename, 'r') as zh:
                self.assertEqual(util.get_maff_pages(zh), [
                    ('Example MAFF', 'http://example.com/', 'Mon, 25 Dec 2017 17:27:46 GMT', 'webpage1/index.html', 'UTF-8'),
                    (None, None, None, 'webpage2/index.html', None),
                    (None, None, None, 'webpage3/index.svg', None),
                    ])
        finally:
            try:
                os.remove(maff_filename)
            except FileNotFoundError:
                pass

    @mock.patch('sys.stderr', io.StringIO())
    def test_encrypt(self):
        self.assertEqual(util.encrypt('1234', 'salt', 'plain'),
            '1234salt'
            )
        self.assertEqual(util.encrypt('1234', 'salt', 'md5'),
            '1fadcf6eb4345975be993f237c51d426'
            )
        self.assertEqual(util.encrypt('1234', 'salt', 'sha1'),
            '40c95464b7eacddb5572af5468ffb1cdb5b13f35'
            )
        self.assertEqual(util.encrypt('1234', 'salt', 'sha256'),
            '4b3bed8af7b7612e8c1e25f63ba24496f5b16b2df44efb2db7ce3cb24b7e96f7'
            )
        self.assertEqual(util.encrypt('1234', 'salt', 'unknown'),
            '1234salt'
            )

if __name__ == '__main__':
    unittest.main()
