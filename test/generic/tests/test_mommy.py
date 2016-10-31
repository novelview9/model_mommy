# -*- coding:utf-8 -*-
from decimal import Decimal

from django import VERSION
from django.test import TestCase
from django.db.models import Manager
from django.db.models.signals import m2m_changed

from model_mommy import mommy
from model_mommy import random_gen
from model_mommy.exceptions import ModelNotFound, AmbiguousModelName, InvalidQuantityException
from model_mommy.timezone import smart_datetime as datetime

from mock import patch

from test.generic import models


class ModelFinderTest(TestCase):
    def test_unicode_regression(self):
        obj = mommy.prepare('generic.Person')
        self.assertIsInstance(obj, models.Person)

    def test_model_class(self):
        obj = mommy.prepare(models.Person)
        self.assertIsInstance(obj, models.Person)

    def test_app_model_string(self):
        obj = mommy.prepare('generic.Person')
        self.assertIsInstance(obj, models.Person)

    def test_model_string(self):
        obj = mommy.prepare('Person')
        self.assertIsInstance(obj, models.Person)

    def test_raise_on_ambiguous_model_string(self):
        with self.assertRaises(AmbiguousModelName):
            mommy.prepare('Ambiguous')

    def test_raise_model_not_found(self):
        with self.assertRaises(ModelNotFound):
            mommy.Mommy('non_existing.Model')

        with self.assertRaises(ModelNotFound):
            mommy.Mommy('NonExistingModel')


class MommyCreatesSimpleModel(TestCase):

    def test_consider_real_django_fields_only(self):
        id_ = models.ModelWithImpostorField._meta.get_field('id')
        with patch.object(mommy.Mommy, 'get_fields') as mock:
            f = Manager()
            f.name = 'foo'
            mock.return_value = [id_, f]
            try:
                mommy.make(models.ModelWithImpostorField)
            except TypeError:
                self.fail('TypeError raised')

    def test_make_should_create_one_object(self):
        person = mommy.make(models.Person)
        self.assertIsInstance(person, models.Person)

        # makes sure it is the person we created
        self.assertTrue(models.Person.objects.filter(id=person.id))

    def test_prepare_should_not_persist_one_object(self):
        person = mommy.prepare(models.Person)
        self.assertIsInstance(person, models.Person)

        # makes sure database is clean
        self.assertEqual(models.Person.objects.all().count(), 0)

        self.assertEqual(person.id, None)

    def test_non_abstract_model_creation(self):
        person = mommy.make(models.NonAbstractPerson, name='bob', happy=False)
        self.assertIsInstance(person, models.NonAbstractPerson)
        self.assertEqual('bob', person.name)
        self.assertFalse(person.happy)

    def test_multiple_inheritance_creation(self):
        multiple = mommy.make(models.DummyMultipleInheritanceModel)
        self.assertIsInstance(multiple, models.DummyMultipleInheritanceModel)
        self.assertTrue(models.Person.objects.filter(id=multiple.id))
        self.assertTrue(models.DummyDefaultFieldsModel.objects.filter(default_id=multiple.default_id))


class MommyRepeatedCreatesSimpleModel(TestCase):

    def test_make_should_create_objects_respecting_quantity_parameter(self):
        people = mommy.make(models.Person, _quantity=5)
        self.assertEqual(models.Person.objects.count(), 5)

        people = mommy.make(models.Person, _quantity=5, name="George Washington")
        self.assertTrue(all(p.name == "George Washington" for p in people))

    def test_make_raises_correct_exception_if_invalid_quantity(self):
        self.assertRaises(
            InvalidQuantityException, mommy.make, model=models.Person, _quantity="hi"
        )
        self.assertRaises(
            InvalidQuantityException, mommy.make, model=models.Person, _quantity=-1
        )
        self.assertRaises(
            InvalidQuantityException, mommy.make, model=models.Person, _quantity=0
        )

    def test_prepare_should_create_objects_respecting_quantity_parameter(self):
        people = mommy.prepare(models.Person, _quantity=5)
        self.assertEqual(len(people), 5)
        self.assertTrue(all(not p.id for p in people))

        people = mommy.prepare(models.Person, _quantity=5, name="George Washington")
        self.assertTrue(all(p.name == "George Washington" for p in people))

    def test_prepare_raises_correct_exception_if_invalid_quantity(self):
        self.assertRaises(
            InvalidQuantityException, mommy.prepare, model=models.Person, _quantity="hi"
        )
        self.assertRaises(
            InvalidQuantityException, mommy.prepare, model=models.Person, _quantity=-1
        )
        self.assertRaises(
            InvalidQuantityException, mommy.prepare, model=models.Person, _quantity=0
        )


class MommyCreatesAssociatedModels(TestCase):

    def test_dependent_models_with_ForeignKey(self):
        dog = mommy.make(models.Dog)
        self.assertIsInstance(dog.owner, models.Person)

    def test_foreign_key_on_parent_should_create_one_object(self):
        '''
        Foreign key on parent gets created twice. Once for
        parent oject and another time for child object
        '''
        person_count = models.Person.objects.count()
        mommy.make(models.GuardDog)
        self.assertEqual(models.Person.objects.count(), person_count + 1)

    def test_auto_now_add_on_parent_should_work(self):
        '''
        Foreign key on parent gets created twice. Once for
        parent oject and another time for child object
        '''
        person_count = models.Person.objects.count()
        dog = mommy.make(models.GuardDog)
        self.assertNotEqual(dog.created, None)

    def test_attrs_on_related_model_through_parent(self):
        '''
        Foreign key on parent gets created twice. Once for
        parent oject and another time for child object
        '''
        mommy.make(models.GuardDog, owner__name='john')
        for person in models.Person.objects.all():
            self.assertEqual(person.name, 'john')

    def test_prepare_fk(self):
        dog = mommy.prepare(models.Dog)
        self.assertIsInstance(dog, models.Dog)
        self.assertIsInstance(dog.owner, models.Person)

        self.assertEqual(models.Person.objects.all().count(), 0)
        self.assertEqual(models.Dog.objects.all().count(), 0)

    def test_create_one_to_one(self):
        lonely_person = mommy.make(models.LonelyPerson)

        self.assertEqual(models.LonelyPerson.objects.all().count(), 1)
        self.assertTrue(isinstance(lonely_person.only_friend, models.Person))
        self.assertEqual(models.Person.objects.all().count(), 1)

    def test_create_many_to_many_if_flagged(self):
        store = mommy.make(models.Store, make_m2m=True)
        self.assertEqual(store.employees.count(), 5)
        self.assertEqual(store.customers.count(), 5)

    def test_regresstion_many_to_many_field_is_accepted_as_kwargs(self):
        employees = mommy.make(models.Person, _quantity=3)
        customers = mommy.make(models.Person, _quantity=3)

        store = mommy.make(models.Store, employees=employees, customers=customers)

        self.assertEqual(store.employees.count(), 3)
        self.assertEqual(store.customers.count(), 3)
        self.assertEqual(models.Person.objects.count(), 6)

    def test_create_many_to_many_with_set_default_quantity(self):
        store = mommy.make(models.Store, make_m2m=True)
        self.assertEqual(store.employees.count(), mommy.MAX_MANY_QUANTITY)
        self.assertEqual(store.customers.count(), mommy.MAX_MANY_QUANTITY)

    def test_create_many_to_many_with_through_option(self):
        """
         This does not works
        """
        # School student's attr is a m2m relationship with a model through
        school = mommy.make(models.School, make_m2m=True)
        self.assertEqual(models.School.objects.count(), 1)
        self.assertEqual(school.students.count(), mommy.MAX_MANY_QUANTITY)
        self.assertEqual(models.SchoolEnrollment.objects.count(), mommy.MAX_MANY_QUANTITY)
        self.assertEqual(models.Person.objects.count(), mommy.MAX_MANY_QUANTITY)

    def test_does_not_create_many_to_many_as_default(self):
        store = mommy.make(models.Store)
        self.assertEqual(store.employees.count(), 0)
        self.assertEqual(store.customers.count(), 0)

    def test_does_not_create_nullable_many_to_many_for_relations(self):
        classroom = mommy.make(models.Classroom, make_m2m=False)
        self.assertEqual(classroom.students.count(), 0)

    def test_nullable_many_to_many_is_not_created_even_if_flagged(self):
        classroom = mommy.make(models.Classroom, make_m2m=True)
        self.assertEqual(classroom.students.count(), 0)

    def test_m2m_changed_signal_is_fired(self):
        # Use object attrs instead of mocks for Django 1.4 compat
        self.m2m_changed_fired = False
        def test_m2m_changed(*args, **kwargs):
            self.m2m_changed_fired = True
        m2m_changed.connect(test_m2m_changed, dispatch_uid='test_m2m_changed')
        mommy.make(models.Store, make_m2m=True)
        self.assertTrue(self.m2m_changed_fired)

    def test_simple_creating_person_with_parameters(self):
        kid = mommy.make(models.Person, happy=True, age=10, name='Mike')
        self.assertEqual(kid.age, 10)
        self.assertEqual(kid.happy, True)
        self.assertEqual(kid.name, 'Mike')

    def test_creating_person_from_factory_using_paramters(self):
        person_mom = mommy.Mommy(models.Person)
        person = person_mom.make(happy=False, age=20, gender='M', name='John')
        self.assertEqual(person.age, 20)
        self.assertEqual(person.happy, False)
        self.assertEqual(person.name, 'John')
        self.assertEqual(person.gender, 'M')

    def test_ForeignKey_model_field_population(self):
        dog = mommy.make(models.Dog, breed='X1', owner__name='Bob')
        self.assertEqual('X1', dog.breed)
        self.assertEqual('Bob', dog.owner.name)

    def test_ForeignKey_model_field_population_should_work_with_prepare(self):
        dog = mommy.prepare(models.Dog, breed='X1', owner__name='Bob')
        self.assertEqual('X1', dog.breed)
        self.assertEqual('Bob', dog.owner.name)

    def test_ForeignKey_model_field_population_for_not_required_fk(self):
        user = mommy.make(models.User, profile__email="a@b.com")
        self.assertEqual('a@b.com', user.profile.email)

    def test_does_not_creates_null_ForeignKey(self):
        user = mommy.make(models.User)
        self.assertFalse(user.profile)

    def test_passing_m2m_value(self):
        store = mommy.make(models.Store, customers=[mommy.make(models.Person)])
        self.assertEqual(store.customers.count(), 1)

    def test_ensure_recursive_ForeignKey_population(self):
        bill = mommy.make(models.PaymentBill, user__profile__email="a@b.com")
        self.assertEqual('a@b.com', bill.user.profile.email)

    def test_field_lookup_for_m2m_relationship(self):
        store = mommy.make(models.Store, suppliers__gender='M')
        suppliers = store.suppliers.all()
        self.assertTrue(suppliers)
        for supplier in suppliers:
            self.assertEqual('M', supplier.gender)

    def test_field_lookup_for_one_to_one_relationship(self):
        lonely_person = mommy.make(models.LonelyPerson, only_friend__name='Bob')
        self.assertEqual('Bob', lonely_person.only_friend.name)

    def test_allow_create_fkey_related_model(self):
        try:
            person = mommy.make(models.Person, dog_set=[mommy.make(models.Dog),
                                                        mommy.make(models.Dog)])
        except TypeError:
            self.fail('type error raised')

        self.assertEqual(person.dog_set.count(), 2)


class HandlingUnsupportedModels(TestCase):
    def test_unsupported_model_raises_an_explanatory_exception(self):
        try:
            mommy.make(models.UnsupportedModel)
            self.fail("Should have raised a TypeError")
        except TypeError as e:
            self.assertTrue('not supported' in repr(e))


class HandlingModelsWithGenericRelationFields(TestCase):
    def test_create_model_with_generic_relation(self):
        dummy = mommy.make(models.DummyGenericRelationModel)
        self.assertIsInstance(dummy, models.DummyGenericRelationModel)


class HandlingContentTypeField(TestCase):
    def test_create_model_with_contenttype_field(self):
        dummy = mommy.make(models.DummyGenericForeignKeyModel)
        self.assertIsInstance(dummy, models.DummyGenericForeignKeyModel)
try:
    from django.test import SimpleTestCase
    class HandlingContentTypeFieldNoQueries(SimpleTestCase):
        def test_create_model_with_contenttype_field(self):
            dummy = mommy.prepare(models.DummyGenericForeignKeyModel)
            self.assertIsInstance(dummy, models.DummyGenericForeignKeyModel)
except ImportError:
    pass


class SkipNullsTestCase(TestCase):
    def test_skip_null(self):
        dummy = mommy.make(models.DummyNullFieldsModel)
        self.assertEqual(dummy.null_foreign_key, None)
        self.assertEqual(dummy.null_integer_field, None)


class FillNullsTestCase(TestCase):
    def test_create_nullable_many_to_many_if_flagged_and_fill_field_optional(self):
        classroom = mommy.make(models.Classroom, make_m2m=True, _fill_optional=[
            'students'])
        self.assertEqual(classroom.students.count(), 5)

    def test_create_nullable_many_to_many_if_flagged_and_fill_optional(self):
        classroom = mommy.make(models.Classroom, make_m2m=True, _fill_optional=True)
        self.assertEqual(classroom.students.count(), 5)

    def test_nullable_many_to_many_is_not_created_if_not_flagged_and_fill_optional(self):
        classroom = mommy.make(models.Classroom, make_m2m=False, _fill_optional=True)
        self.assertEqual(classroom.students.count(), 0)


class SkipBlanksTestCase(TestCase):
    def test_skip_blank(self):
        dummy = mommy.make(models.DummyBlankFieldsModel)
        self.assertEqual(dummy.blank_char_field, '')
        self.assertEqual(dummy.blank_text_field, '')


class FillBlanksTestCase(TestCase):
    def test_fill_field_optional(self):
        dummy = mommy.make(models.DummyBlankFieldsModel, _fill_optional=['blank_char_field'])
        self.assertEqual(len(dummy.blank_char_field), 50)

    def test_fill_many_optional(self):
        dummy = mommy.make(models.DummyBlankFieldsModel, _fill_optional=['blank_char_field', 'blank_text_field'])
        self.assertEqual(len(dummy.blank_text_field), 300)

    def test_fill_all_optional(self):
        dummy = mommy.make(models.DummyBlankFieldsModel, _fill_optional=True)
        self.assertEqual(len(dummy.blank_char_field), 50)
        self.assertEqual(len(dummy.blank_text_field), 300)

    def test_fill_optional_with_integer(self):
        with self.assertRaises(TypeError):
            mommy.make(models.DummyBlankFieldsModel, _fill_optional=1)


class FillAutoFieldsTestCase(TestCase):

    def test_fill_autofields_with_provided_value(self):
        mommy.make(models.DummyEmptyModel, id=237)
        saved_dummy = models.DummyEmptyModel.objects.get()
        self.assertEqual(saved_dummy.id, 237)

    def test_keeps_prepare_autovalues(self):
        dummy = mommy.prepare(models.DummyEmptyModel, id=543)
        self.assertEqual(dummy.id, 543)
        dummy.save()
        saved_dummy = models.DummyEmptyModel.objects.get()
        self.assertEqual(saved_dummy.id, 543)


class SkipDefaultsTestCase(TestCase):
    def test_skip_fields_with_default(self):
        dummy = mommy.make(models.DummyDefaultFieldsModel)
        self.assertEqual(dummy.default_char_field, 'default')
        self.assertEqual(dummy.default_text_field, 'default')
        self.assertEqual(dummy.default_int_field, 123)
        self.assertEqual(dummy.default_float_field, 123.0)
        self.assertEqual(dummy.default_date_field, '2012-01-01')
        self.assertEqual(dummy.default_date_time_field, datetime(2012, 1, 1))
        self.assertEqual(dummy.default_time_field, '00:00:00')
        self.assertEqual(dummy.default_decimal_field, Decimal('0'))
        self.assertEqual(dummy.default_email_field, 'foo@bar.org')
        self.assertEqual(dummy.default_slug_field, 'a-slug')


class MommyHandlesModelWithNext(TestCase):
    def test_creates_instance_for_model_with_next(self):
        instance = mommy.make(
            models.BaseModelForNext,
            fk=mommy.make(models.ModelWithNext),
        )

        self.assertTrue(instance.id)
        self.assertTrue(instance.fk.id)
        self.assertTrue(instance.fk.attr)
        self.assertEqual('foo', instance.fk.next())


class MommyHandlesModelWithList(TestCase):
    def test_creates_instance_for_model_with_list(self):
        instance = mommy.make(
            models.BaseModelForList,
            fk=["foo"]
        )

        self.assertTrue(instance.id)
        self.assertEqual(["foo"], instance.fk)

if VERSION < (1, 4):
    from test.generic.forms import DummyIPAddressFieldForm

    class MommyGeneratesIPAdresses(TestCase):
        def test_create_model_with_valid_ipv4(self):
            form_data = {
                'ipv4_field': random_gen.gen_ipv4(),
            }
            self.assertTrue(DummyIPAddressFieldForm(form_data).is_valid())
else:
    from test.generic.forms import DummyGenericIPAddressFieldForm

    class MommyGeneratesIPAdresses(TestCase):
        def test_create_model_with_valid_ips(self):
            form_data = {
                'ipv4_field': random_gen.gen_ipv4(),
                'ipv6_field': random_gen.gen_ipv6(),
                'ipv46_field': random_gen.gen_ipv46(),
            }
            self.assertTrue(DummyGenericIPAddressFieldForm(form_data).is_valid())
