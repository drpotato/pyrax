#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from mock import patch
from mock import MagicMock as Mock

from pyrax.clouddatabases import CloudDatabaseClient
from pyrax.clouddatabases import CloudDatabaseDatabase
from pyrax.clouddatabases import CloudDatabaseFlavor
from pyrax.clouddatabases import CloudDatabaseInstance
from pyrax.clouddatabases import CloudDatabaseUser
from pyrax.clouddatabases import assure_instance
from pyrax.clouddatabases import CloudDatabaseUserManager
import pyrax.exceptions as exc
import pyrax.utils as utils

import fakes

example_uri = "http://example.com"


class CloudDatabasesTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(CloudDatabasesTest, self).__init__(*args, **kwargs)

    def setUp(self):
        self.instance = fakes.FakeDatabaseInstance()
        self.client = fakes.FakeDatabaseClient()

    def tearDown(self):
        pass

    def test_assure_instance(self):
        class TestClient(object):
            _manager = fakes.FakeManager()

            @assure_instance
            def test_method(self, instance):
                return instance

        client = TestClient()
        client._manager.get = Mock(return_value=self.instance)
        # Pass the instance
        ret = client.test_method(self.instance)
        self.assertTrue(ret is self.instance)
        # Pass the ID
        ret = client.test_method(self.instance.id)
        self.assertTrue(ret is self.instance)

    @patch("pyrax.manager.BaseManager", new=fakes.FakeManager)
    def test_instantiate_instance(self):
        inst = CloudDatabaseInstance(fakes.FakeManager(), {"id": 42,
                "volume": {"size": 1, "used": 0.2}})
        self.assertTrue(isinstance(inst, CloudDatabaseInstance))

    def test_list_databases(self):
        inst = self.instance
        sav = inst._database_manager.list
        inst._database_manager.list = Mock()
        limit = utils.random_unicode()
        marker = utils.random_unicode()
        inst.list_databases(limit=limit, marker=marker)
        inst._database_manager.list.assert_called_once_with(limit=limit,
                marker=marker)
        inst._database_manager.list = sav

    def test_list_users(self):
        inst = self.instance
        sav = inst._user_manager.list
        inst._user_manager.list = Mock()
        limit = utils.random_unicode()
        marker = utils.random_unicode()
        inst.list_users(limit=limit, marker=marker)
        inst._user_manager.list.assert_called_once_with(limit=limit, marker=marker)
        inst._user_manager.list = sav

    def test_get_database(self):
        inst = self.instance
        sav = inst.list_databases
        db1 = fakes.FakeEntity()
        db1.name = "a"
        db2 = fakes.FakeEntity()
        db2.name = "b"
        inst.list_databases = Mock(return_value=[db1, db2])
        ret = inst.get_database("a")
        self.assertEqual(ret, db1)
        inst.list_databases = sav

    def test_get_database_bad(self):
        inst = self.instance
        sav = inst.list_databases
        db1 = fakes.FakeEntity()
        db1.name = "a"
        db2 = fakes.FakeEntity()
        db2.name = "b"
        inst.list_databases = Mock(return_value=[db1, db2])
        self.assertRaises(exc.NoSuchDatabase, inst.get_database, "z")
        inst.list_databases = sav

    def test_create_database(self):
        inst = self.instance
        sav = inst._database_manager.create
        inst._database_manager.create = Mock()
        inst._database_manager.find = Mock()
        db = inst.create_database(name="test")
        inst._database_manager.create.assert_called_once_with(name="test",
                character_set="utf8", collate="utf8_general_ci",
                return_none=True)
        inst._database_manager.create = sav

    def test_create_user(self):
        inst = self.instance
        sav = inst._user_manager.create
        inst._user_manager.create = Mock()
        inst._user_manager.find = Mock()
        inst.create_user(name="test", password="testpw",
                database_names="testdb")
        inst._user_manager.create.assert_called_once_with(name="test",
                password="testpw",
        database_names=["testdb"], return_none=True)
        inst._user_manager.create = sav

    def test_delete_database(self):
        inst = self.instance
        sav = inst._database_manager.delete
        inst._database_manager.delete = Mock()
        inst.delete_database("dbname")
        inst._database_manager.delete.assert_called_once_with("dbname")
        inst._database_manager.delete = sav

    def test_delete_user(self):
        inst = self.instance
        sav = inst._user_manager.delete
        inst._user_manager.delete = Mock()
        inst.delete_user("username")
        inst._user_manager.delete.assert_called_once_with("username")
        inst._user_manager.delete = sav

    def test_enable_root_user(self):
        inst = self.instance
        pw = utils.random_unicode()
        fake_body = {"user": {"password": pw}}
        inst.manager.api.method_post = Mock(return_value=(None, fake_body))
        ret = inst.enable_root_user()
        call_uri = "/instances/%s/root" % inst.id
        inst.manager.api.method_post.assert_called_once_with(call_uri)
        self.assertEqual(ret, pw)

    def test_root_user_status(self):
        inst = self.instance
        fake_body = {"rootEnabled": True}
        inst.manager.api.method_get = Mock(return_value=(None, fake_body))
        ret = inst.root_user_status()
        call_uri = "/instances/%s/root" % inst.id
        inst.manager.api.method_get.assert_called_once_with(call_uri)
        self.assertTrue(ret)

    def test_restart(self):
        inst = self.instance
        inst.manager.action = Mock()
        ret = inst.restart()
        inst.manager.action.assert_called_once_with(inst, "restart")

    def test_resize(self):
        inst = self.instance
        flavor_ref = utils.random_unicode()
        inst.manager.api._get_flavor_ref = Mock(return_value=flavor_ref)
        fake_body = {"flavorRef": flavor_ref}
        inst.manager.action = Mock()
        ret = inst.resize(42)
        call_uri = "/instances/%s/action" % inst.id
        inst.manager.action.assert_called_once_with(inst, "resize",
                body=fake_body)

    def test_resize_volume_too_small(self):
        inst = self.instance
        inst.volume.get = Mock(return_value=2)
        self.assertRaises(exc.InvalidVolumeResize, inst.resize_volume, 1)

    def test_resize_volume(self):
        inst = self.instance
        fake_body = {"volume": {"size": 2}}
        inst.manager.action = Mock()
        ret = inst.resize_volume(2)
        inst.manager.action.assert_called_once_with(inst, "resize",
                body=fake_body)

    def test_resize_volume_direct(self):
        inst = self.instance
        vol = inst.volume
        fake_body = {"volume": {"size": 2}}
        inst.manager.action = Mock()
        ret = vol.resize(2)
        inst.manager.action.assert_called_once_with(inst, "resize",
                body=fake_body)

    def test_volume_get(self):
        inst = self.instance
        vol = inst.volume
        att = vol.size
        using_get = vol.get("size")
        self.assertEqual(att, using_get)

    def test_volume_get_fail(self):
        inst = self.instance
        vol = inst.volume
        self.assertRaises(AttributeError, vol.get, "fake")

    def test_get_flavor_property(self):
        inst = self.instance
        inst._loaded = True
        flavor = inst.flavor
        self.assertTrue(isinstance(flavor, CloudDatabaseFlavor))

    def test_set_flavor_property_dict(self):
        inst = self.instance
        inst._loaded = True
        inst.flavor = {"name": "test"}
        self.assertTrue(isinstance(inst.flavor, CloudDatabaseFlavor))

    def test_set_flavor_property_instance(self):
        inst = self.instance
        inst._loaded = True
        flavor = CloudDatabaseFlavor(inst.manager, {"name": "test"})
        inst.flavor = flavor
        self.assertTrue(isinstance(inst.flavor, CloudDatabaseFlavor))

    @patch("pyrax.manager.BaseManager", new=fakes.FakeManager)
    def test_list_databases_for_instance(self):
        clt = self.client
        inst = self.instance
        sav = inst.list_databases
        limit = utils.random_unicode()
        marker = utils.random_unicode()
        inst.list_databases = Mock(return_value=["db"])
        ret = clt.list_databases(inst, limit=limit, marker=marker)
        self.assertEqual(ret, ["db"])
        inst.list_databases.assert_called_once_with(limit=limit, marker=marker)
        inst.list_databases = sav

    @patch("pyrax.manager.BaseManager", new=fakes.FakeManager)
    def test_create_database_for_instance(self):
        clt = self.client
        inst = self.instance
        sav = inst.create_database
        inst.create_database = Mock(return_value=["db"])
        nm = utils.random_unicode()
        ret = clt.create_database(inst, nm)
        self.assertEqual(ret, ["db"])
        inst.create_database.assert_called_once_with(nm,
                character_set=None, collate=None)
        inst.create_database = sav

    def test_clt_get_database(self):
        clt = self.client
        inst = self.instance
        inst.get_database = Mock()
        nm = utils.random_unicode()
        clt.get_database(inst, nm)
        inst.get_database.assert_called_once_with(nm)

    @patch("pyrax.manager.BaseManager", new=fakes.FakeManager)
    def test_delete_database_for_instance(self):
        clt = self.client
        inst = self.instance
        sav = inst.delete_database
        inst.delete_database = Mock()
        nm = utils.random_unicode()
        clt.delete_database(inst, nm)
        inst.delete_database.assert_called_once_with(nm)
        inst.delete_database = sav

    @patch("pyrax.manager.BaseManager", new=fakes.FakeManager)
    def test_list_users_for_instance(self):
        clt = self.client
        inst = self.instance
        sav = inst.list_users
        limit = utils.random_unicode()
        marker = utils.random_unicode()
        inst.list_users = Mock(return_value=["user"])
        ret = clt.list_users(inst, limit=limit, marker=marker)
        self.assertEqual(ret, ["user"])
        inst.list_users.assert_called_once_with(limit=limit, marker=marker)
        inst.list_users = sav

    def test_create_user_for_instance(self):
        clt = self.client
        inst = self.instance
        sav = inst.create_user
        inst.create_user = Mock()
        nm = utils.random_unicode()
        pw = utils.random_unicode()
        ret = clt.create_user(inst, nm, pw, ["db"])
        inst.create_user.assert_called_once_with(name=nm, password=pw,
                database_names=["db"])
        inst.create_user = sav

    @patch("pyrax.manager.BaseManager", new=fakes.FakeManager)
    def test_delete_user_for_instance(self):
        clt = self.client
        inst = self.instance
        sav = inst.delete_user
        inst.delete_user = Mock()
        nm = utils.random_unicode()
        clt.delete_user(inst, nm)
        inst.delete_user.assert_called_once_with(nm)
        inst.delete_user = sav

    @patch("pyrax.manager.BaseManager", new=fakes.FakeManager)
    def test_enable_root_user_for_instance(self):
        clt = self.client
        inst = self.instance
        sav = inst.enable_root_user
        inst.enable_root_user = Mock()
        clt.enable_root_user(inst)
        inst.enable_root_user.assert_called_once_with()
        inst.enable_root_user = sav

    @patch("pyrax.manager.BaseManager", new=fakes.FakeManager)
    def test_root_user_status_for_instance(self):
        clt = self.client
        inst = self.instance
        sav = inst.root_user_status
        inst.root_user_status = Mock()
        clt.root_user_status(inst)
        inst.root_user_status.assert_called_once_with()
        inst.root_user_status = sav

    @patch("pyrax.manager.BaseManager", new=fakes.FakeManager)
    def test_get_user_by_client(self):
        clt = self.client
        inst = self.instance
        sav = inst.get_user
        inst.get_user = Mock()
        fakeuser = utils.random_unicode()
        clt.get_user(inst, fakeuser)
        inst.get_user.assert_called_once_with(fakeuser)
        inst.get_user = sav

    def test_get_user(self):
        inst = self.instance
        good_name = utils.random_unicode()
        user = fakes.FakeDatabaseUser(manager=None, info={"name": good_name})
        inst._user_manager.get = Mock(return_value=user)
        returned = inst.get_user(good_name)
        self.assertEqual(returned, user)

    def test_get_user_fail(self):
        inst = self.instance
        bad_name = utils.random_unicode()
        inst._user_manager.get = Mock(side_effect=exc.NoSuchDatabaseUser())
        self.assertRaises(exc.NoSuchDatabaseUser, inst.get_user, bad_name)

    def test_get_db_names(self):
        inst = self.instance
        mgr = inst._user_manager
        mgr.instance = inst
        dbname1 = utils.random_ascii()
        dbname2 = utils.random_ascii()
        sav = inst.list_databases
        inst.list_databases = Mock(return_value=((dbname1, dbname2)))
        resp = mgr._get_db_names(dbname1)
        self.assertEqual(resp, [dbname1])
        inst.list_databases = sav

    def test_get_db_names_not_strict(self):
        inst = self.instance
        mgr = inst._user_manager
        mgr.instance = inst
        dbname1 = utils.random_ascii()
        dbname2 = utils.random_ascii()
        sav = inst.list_databases
        inst.list_databases = Mock(return_value=((dbname1, dbname2)))
        resp = mgr._get_db_names("BAD", strict=False)
        self.assertEqual(resp, ["BAD"])
        inst.list_databases = sav

    def test_get_db_names_fail(self):
        inst = self.instance
        mgr = inst._user_manager
        mgr.instance = inst
        dbname1 = utils.random_ascii()
        dbname2 = utils.random_ascii()
        sav = inst.list_databases
        inst.list_databases = Mock(return_value=((dbname1, dbname2)))
        self.assertRaises(exc.NoSuchDatabase, mgr._get_db_names, "BAD")
        inst.list_databases = sav

    def test_change_user_password(self):
        inst = self.instance
        fakeuser = utils.random_unicode()
        newpass = utils.random_unicode()
        resp = fakes.FakeResponse()
        resp.status = 202
        inst._user_manager.api.method_put = Mock(return_value=(resp, {}))
        inst.change_user_password(fakeuser, newpass)
        inst._user_manager.api.method_put.assert_called_once_with("/None",
                body={"users": [{"password": newpass, "name": fakeuser}]})

    def test_list_user_access(self):
        inst = self.instance
        dbname1 = utils.random_ascii()
        dbname2 = utils.random_ascii()
        acc = {"databases": [{"name": dbname1}, {"name": dbname2}]}
        inst._user_manager.api.method_get = Mock(return_value=(None, acc))
        db_list = inst.list_user_access("fakeuser")
        self.assertEqual(len(db_list), 2)
        self.assertTrue(db_list[0].name in (dbname1, dbname2))

    def test_grant_user_access(self):
        inst = self.instance
        fakeuser = utils.random_ascii()
        dbname1 = utils.random_ascii()
        inst._user_manager.api.method_put = Mock(return_value=(None, None))
        inst.grant_user_access(fakeuser, dbname1, strict=False)
        inst._user_manager.api.method_put.assert_called_once_with(
                "/None/%s/databases" % fakeuser, body={"databases": [{"name":
                dbname1}]})

    def test_revoke_user_access(self):
        inst = self.instance
        fakeuser = utils.random_ascii()
        dbname1 = utils.random_ascii()
        inst._user_manager.api.method_delete = Mock(return_value=(None, None))
        inst.revoke_user_access(fakeuser, dbname1, strict=False)
        inst._user_manager.api.method_delete.assert_called_once_with(
                "/None/%s/databases/%s" % (fakeuser, dbname1))

    def test_clt_change_user_password(self):
        clt = self.client
        inst = self.instance
        inst.change_user_password = Mock()
        user = utils.random_unicode()
        pw = utils.random_unicode()
        clt.change_user_password(inst, user, pw)
        inst.change_user_password.assert_called_once_with(user, pw)

    def test_clt_list_user_access(self):
        clt = self.client
        inst = self.instance
        inst.list_user_access = Mock()
        user = utils.random_unicode()
        clt.list_user_access(inst, user)
        inst.list_user_access.assert_called_once_with(user)

    def test_clt_grant_user_access(self):
        clt = self.client
        inst = self.instance
        inst.grant_user_access = Mock()
        user = utils.random_unicode()
        db_names = utils.random_unicode()
        clt.grant_user_access(inst, user, db_names)
        inst.grant_user_access.assert_called_once_with(user, db_names,
                strict=True)

    def test_clt_revoke_user_access(self):
        clt = self.client
        inst = self.instance
        inst.revoke_user_access = Mock()
        user = utils.random_unicode()
        db_names = utils.random_unicode()
        clt.revoke_user_access(inst, user, db_names)
        inst.revoke_user_access.assert_called_once_with(user, db_names,
                strict=True)

    def test_clt_restart(self):
        clt = self.client
        inst = self.instance
        inst.restart = Mock()
        clt.restart(inst)
        inst.restart.assert_called_once_with()


    @patch("pyrax.manager.BaseManager", new=fakes.FakeManager)
    def test_resize_for_instance(self):
        clt = self.client
        inst = self.instance
        sav = inst.resize
        inst.resize = Mock()
        clt.resize(inst, "flavor")
        inst.resize.assert_called_once_with("flavor")
        inst.resize = sav

    def test_get_limits(self):
        self.assertRaises(NotImplementedError, self.client.get_limits)

    @patch("pyrax.manager.BaseManager", new=fakes.FakeManager)
    def test_list_flavors(self):
        clt = self.client
        clt._flavor_manager.list = Mock()
        limit = utils.random_unicode()
        marker = utils.random_unicode()
        clt.list_flavors(limit=limit, marker=marker)
        clt._flavor_manager.list.assert_called_once_with(limit=limit,
                marker=marker)

    @patch("pyrax.manager.BaseManager", new=fakes.FakeManager)
    def test_get_flavor(self):
        clt = self.client
        clt._flavor_manager.get = Mock()
        clt.get_flavor("flavorid")
        clt._flavor_manager.get.assert_called_once_with("flavorid")

    @patch("pyrax.manager.BaseManager", new=fakes.FakeManager)
    def test_get_flavor_ref_for_obj(self):
        clt = self.client
        info = {"id": 1,
                "name": "test_flavor",
                "ram": 42,
                "links": [{
                    "href": example_uri,
                    "rel": "self"}]}
        flavor_obj = CloudDatabaseFlavor(clt._manager, info)
        ret = clt._get_flavor_ref(flavor_obj)
        self.assertEqual(ret, example_uri)

    @patch("pyrax.manager.BaseManager", new=fakes.FakeManager)
    def test_get_flavor_ref_for_id(self):
        clt = self.client
        info = {"id": 1,
                "name": "test_flavor",
                "ram": 42,
                "links": [{
                    "href": example_uri,
                    "rel": "self"}]}
        flavor_obj = CloudDatabaseFlavor(clt._manager, info)
        sav = clt.get_flavor
        clt.get_flavor = Mock(return_value=flavor_obj)
        ret = clt._get_flavor_ref(1)
        self.assertEqual(ret, example_uri)
        clt.get_flavor = sav

    @patch("pyrax.manager.BaseManager", new=fakes.FakeManager)
    def test_get_flavor_ref_for_name(self):
        clt = self.client
        info = {"id": 1,
                "name": "test_flavor",
                "ram": 42,
                "links": [{
                    "href": example_uri,
                    "rel": "self"}]}
        flavor_obj = CloudDatabaseFlavor(clt._manager, info)
        sav_get = clt.get_flavor
        sav_list = clt.list_flavors
        clt.get_flavor = Mock(side_effect=exc.NotFound(""))
        clt.list_flavors = Mock(return_value=[flavor_obj])
        ret = clt._get_flavor_ref("test_flavor")
        self.assertEqual(ret, example_uri)
        clt.get_flavor = sav_get
        clt.list_flavors = sav_list

    @patch("pyrax.manager.BaseManager", new=fakes.FakeManager)
    def test_get_flavor_ref_for_name(self):
        clt = self.client
        info = {"id": 1,
                "name": "test_flavor",
                "ram": 42,
                "links": [{
                    "href": example_uri,
                    "rel": "self"}]}
        flavor_obj = CloudDatabaseFlavor(clt._manager, info)
        sav_get = clt.get_flavor
        sav_list = clt.list_flavors
        clt.get_flavor = Mock(side_effect=exc.NotFound(""))
        clt.list_flavors = Mock(return_value=[flavor_obj])
        ret = clt._get_flavor_ref(42)
        self.assertEqual(ret, example_uri)
        clt.get_flavor = sav_get
        clt.list_flavors = sav_list

    @patch("pyrax.manager.BaseManager", new=fakes.FakeManager)
    def test_get_flavor_ref_not_found(self):
        clt = self.client
        info = {"id": 1,
                "name": "test_flavor",
                "ram": 42,
                "links": [{
                    "href": example_uri,
                    "rel": "self"}]}
        flavor_obj = CloudDatabaseFlavor(clt._manager, info)
        sav_get = clt.get_flavor
        sav_list = clt.list_flavors
        clt.get_flavor = Mock(side_effect=exc.NotFound(""))
        clt.list_flavors = Mock(return_value=[flavor_obj])
        self.assertRaises(exc.FlavorNotFound, clt._get_flavor_ref, "nonsense")
        clt.get_flavor = sav_get
        clt.list_flavors = sav_list

    @patch("pyrax.manager.BaseManager", new=fakes.FakeManager)
    def test_create_body_db(self):
        mgr = self.instance._database_manager
        nm = utils.random_unicode()
        ret = mgr._create_body(nm, character_set="CS", collate="CO")
        expected = {"databases": [
                {"name": nm,
                "character_set": "CS",
                "collate": "CO"}]}
        self.assertEqual(ret, expected)

    @patch("pyrax.manager.BaseManager", new=fakes.FakeManager)
    def test_create_body_user(self):
        inst = self.instance
        mgr = inst._user_manager
        nm = utils.random_unicode()
        pw = utils.random_unicode()
        ret = mgr._create_body(nm, password=pw, database_names=[])
        expected = {"users": [
                {"name": nm,
                "password": pw,
                "databases": []}]}
        self.assertEqual(ret, expected)

    @patch("pyrax.manager.BaseManager", new=fakes.FakeManager)
    def test_create_body_flavor(self):
        clt = self.client
        nm = utils.random_unicode()
        sav = clt._get_flavor_ref
        clt._get_flavor_ref = Mock(return_value=example_uri)
        ret = clt._manager._create_body(nm)
        expected = {"instance": {
                "name": nm,
                "flavorRef": example_uri,
                "volume": {"size": 1},
                "databases": [],
                "users": []}}
        self.assertEqual(ret, expected)
        clt._get_flavor_ref = sav


if __name__ == "__main__":
    unittest.main()
