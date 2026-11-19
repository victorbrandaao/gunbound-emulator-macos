import tempfile
import unittest
import sqlite3
import shutil
from pathlib import Path
import yaml
from operacao.administrar import ROOT,create_account,prepare_network,backup


class OperationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        with sqlite3.connect(ROOT/'gbwc.db') as src:
            with sqlite3.connect(self.root/'gbwc.db') as dst:src.backup(dst)
        shutil.copy2(ROOT/'config.yml',self.root/'config.yml')
    def tearDown(self):self.tmp.cleanup()
    def test_player_is_not_admin_and_has_balances(self):
        create_account('amigoTeste','Senha123',cash=12345,gold=67890,root=self.root)
        c=sqlite3.connect(self.root/'gbwc.db')
        self.assertEqual(c.execute('select Authority from User where Id=?',('amigoTeste',)).fetchone()[0],1)
        self.assertEqual(c.execute('select Cash from Cash where ID=?',('amigoTeste',)).fetchone()[0],12345)
        self.assertEqual(c.execute('select Money from Game where Id=?',('amigoTeste',)).fetchone()[0],67890)
        with self.assertRaises(ValueError):create_account('amigoTeste','outra',root=self.root)
        self.assertEqual(c.execute('select Password from User where Id=?',('amigoTeste',)).fetchone()[0],'Senha123')
        c.close()
    def test_rejects_invalid_credentials_and_balances(self):
        for user,pw,cash in [('bad name','ok',1),('valid','a'*17,1),('valid','ok',-1)]:
            with self.assertRaises(ValueError):create_account(user,pw,cash=cash,root=self.root)
    def test_network_preview_does_not_activate(self):
        original=(self.root/'config.yml').read_bytes()
        p=prepare_network('10.147.17.1','10.147.17.0/24',root=self.root)
        cfg=yaml.safe_load(p.read_text())
        self.assertEqual((self.root/'config.yml').read_bytes(),original)
        self.assertEqual(cfg['broker']['host'],'10.147.17.1')
        self.assertEqual(cfg['gameservers'][0]['accept'],['10.147.17.0/24'])
        self.assertEqual(cfg['gameservers'][0]['udp_allow'],['127.0.0.1/32','10.147.17.1/32'])
        for host,net in [('0.0.0.0','0.0.0.0/0'),('8.8.8.8','8.8.8.0/24'),('10.1.1.1','10.2.0.0/16')]:
            with self.assertRaises(ValueError):prepare_network(host,net,root=self.root)
    def test_backup_is_consistent(self):
        result=backup(self.root)
        c=sqlite3.connect(result)
        self.assertEqual(c.execute('pragma integrity_check').fetchone()[0],'ok');c.close()


if __name__=='__main__':unittest.main()
