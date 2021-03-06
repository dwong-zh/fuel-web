# -*- coding: utf-8 -*-

#    Copyright 2013 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import time

from nailgun import consts
from nailgun.db.sqlalchemy.models import Cluster
from nailgun.test.base import BaseIntegrationTest
from nailgun.test.base import fake_tasks
from nailgun.utils import reverse


class TestCharsetIssues(BaseIntegrationTest):

    def tearDown(self):
        self._wait_for_threads()
        super(TestCharsetIssues, self).tearDown()

    @fake_tasks(override_state={"progress": 100, "status": "ready"})
    def test_deployment_cyrillic_names(self):
        self.env.create(
            cluster_kwargs={"name": u"Тестовый кластер"},
            nodes_kwargs=[
                {"name": u"Контроллер", "pending_addition": True},
                {"name": u"Компьют", "pending_addition": True},
                {"pending_deletion": True},
            ]
        )
        supertask = self.env.launch_deployment()
        self.env.wait_until_task_pending(supertask)

        self.assertEqual(supertask.name, consts.TASK_NAMES.deploy)
        self.assertIn(supertask.status, (consts.TASK_STATUSES.running,
                                         consts.TASK_STATUSES.ready))
        # we have three subtasks here
        # repo connectivity check
        # deletion
        # provision
        # deployment
        self.assertEqual(len(supertask.subtasks), 4)
        self.env.wait_ready(supertask)

    @fake_tasks()
    def test_deletion_during_deployment(self):
        self.env.create(
            cluster_kwargs={
                "name": u"Вася"
            },
            nodes_kwargs=[
                {"status": "ready", "pending_addition": True},
            ]
        )
        cluster_id = self.env.clusters[0].id
        self.app.put(
            reverse(
                'ClusterChangesHandler',
                kwargs={'cluster_id': cluster_id}),
            headers=self.default_headers
        )
        self.app.delete(
            reverse(
                'ClusterHandler',
                kwargs={'obj_id': cluster_id}),
            headers=self.default_headers
        )
        timeout = 10
        timer = time.time()
        while True:
            cluster = self.db.query(Cluster).filter_by(id=cluster_id).first()
            if not cluster:
                break
            if (time.time() - timer) > timeout:
                raise Exception("Cluster deletion timeout")
            time.sleep(0.24)

        self.assertIsNone(cluster)
