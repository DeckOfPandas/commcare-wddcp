import uuid
from django.test import TestCase
from corehq.apps.domain.shortcuts import create_domain
from corehq.form_processor.utils.general import get_local_domain_sql_backend_override, \
    set_local_domain_sql_backend_override, _should_use_sql_backend_in_prod


class UseSqlBackendTest(TestCase):

    def test_local_domain_sql_backend_override_initial_none(self):
        self.assertIsNone(get_local_domain_sql_backend_override(uuid.uuid4().hex))

    def test_local_domain_sql_backend_override(self):
        domain_name = uuid.uuid4().hex
        set_local_domain_sql_backend_override(domain_name)
        self.assertTrue(get_local_domain_sql_backend_override(domain_name))

    def test_test_local_domain_sql_backend_override_overrides(self):
        domain_name = uuid.uuid4().hex
        create_domain(domain_name)
        self.assertFalse(_should_use_sql_backend_in_prod(domain_name))
        set_local_domain_sql_backend_override(domain_name)
        self.assertTrue(_should_use_sql_backend_in_prod(domain_name))
