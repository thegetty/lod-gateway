import os
import sys
import re
import uuid
import copy

from datetime import datetime

# Import support for abstract classes and methods
from abc import ABC, abstractmethod

from app.di import DI

from app.database import Database

from app.utilities import *


class Model(ABC):
    id = None

    _autopopulated = []
    _relationships = None
    _related = None
    _snapshot = None

    # final method; please do not override
    def __new__(cls, *args, **kwargs):
        debug("%s.__new__() called..." % (cls.__name__), level=1)

        cls._relationships = {}

        if cls.initialize:
            if callable(cls.initialize):
                cls.initialize()

        debug(cls._relationships, label="cls._relationships", level=2)

        return super(Model, cls).__new__(cls)

    # final method; please do not override
    def __init__(self, attributes=None):
        debug(
            "%s.__init__(attributes: %s) called..."
            % (self.__class__.__name__, attributes),
            level=1,
        )

        self._related = {}
        self._snapshot = {}

        if isinstance(attributes, dict):
            if len(attributes) > 0:
                for attribute in attributes:
                    if isinstance(attribute, str):
                        value = attributes[attribute]
                        if value:
                            # copy the value into the snapshot so that changes
                            # to the value do not affect the snapshot
                            self._snapshot[attribute] = copy.copy(value)

                            setattr(self, attribute, value)

    def __del__(self):
        debug("%s.__del__() called..." % (self.__class__.__name__), level=1)

    def __str__(self):
        debug("%s.__str__() called..." % (self.__class__.__name__), level=1)

        field = self.getIDField()
        id = getattr(self, field)

        return sprintf("<%s(%s)>" % (self.__class__.__name__, id))

    # final method; please do not override
    def __getattr__(self, name):
        debug(
            "%s.__getattr__(name: %s) called..." % (self.__class__.__name__, name),
            level=2,
        )

        relationships = self.__class__._relationships
        if isinstance(relationships, dict) and len(relationships) > 0:
            if name in relationships:
                relationship = relationships[name]
                if isinstance(relationship, dict):
                    return self.__getRelated(relationship)
                else:
                    # debug("%s.__getattr__(name: %s) Relationship is invalid! Should be defined as a dictionary!" % (self.__class__.__name__, name), error=True)

                    return super().__getattr__(name)
            else:
                # debug("%s.__getattr__(name: %s) Unable to find relationship!" % (self.__class__.__name__, name), error=True)

                return super().__getattr__(name)
        else:
            # debug("%s.__getattr__(name: %s) Unable to find relationships!" % (self.__class__.__name__, name), error=True)

            return super().__getattr__(name)

    # final method; please do not override
    def __setattr__(self, name, value):
        debug(
            "%s.__setattr__(name: %s, value: %s) called..."
            % (self.__class__.__name__, name, value),
            level=2,
        )

        relationships = self.__class__._relationships
        if isinstance(relationships, dict) and len(relationships) > 0:
            if name in relationships:
                relationship = relationships[name]
                if isinstance(relationship, dict):
                    self.__setRelated(relationship, value)
                else:
                    debug(
                        "%s.__setattr__(name: %s) Relationship is invalid! Should be defined as a dictionary!"
                        % (self.__class__.__name__, name),
                        error=True,
                    )

                    super().__setattr__(name, value)
            else:
                # debug("%s.__setattr__(name: %s) Unable to find relationship!" % (self.__class__.__name__, name), error=True)

                super().__setattr__(name, value)
        else:
            # debug("%s.__setattr__(name: %s) Unable to find relationships!" % (self.__class__.__name__, name), error=True)

            super().__setattr__(name, value)

    @classmethod
    def getSource(cls):
        debug("%s.getSource() called..." % (self.__class__.__name__), level=1)
        return None

    @classmethod
    def getIDField(cls):
        return "id"

    # final method; please do not override
    def getID(self):
        field = self.getIDField()
        if isinstance(field, str) and len(field) > 0:
            return getattr(self, field)

        return None

    # final method; please do not override
    @classmethod
    def getModelClass(cls):
        # debug("%s.getModelClass() called..." % (cls.__name__), level=1)

        if len(__name__.split(".")) > 2:
            module = __name__.split(".")[:-1]
            module.append(cls.__name__)
            module = ".".join(module)

            if module in sys.modules:
                klass = getattr(sys.modules[module], cls.__name__)
                if klass:
                    return klass
        else:  # app.model
            if __name__ in sys.modules:
                klass = getattr(sys.modules[__name__], cls.__name__)
                if klass:
                    return klass

        return None

    @classmethod
    def initialize(cls):
        pass

    # final method; please do not override
    @classmethod
    def __joinMethodName(cls, alias=None, model=None, to=None):
        if isinstance(alias, str) and len(alias) > 0:
            _name_ = alias
        elif model:
            _name_ = model.__name__

        if _name_:
            parts = _name_.split("_")
            for index, part in enumerate(parts):
                if index > 0:
                    parts[index] = part.lower().capitalize()
                else:
                    parts[index] = part.lower()

            return sprintf("get%s" % ("".join(parts)))

        return None

    # final method; please do not override
    @classmethod
    def __joinFieldName(cls, field=None, model=None, to=None, alias=None):
        if isinstance(alias, str) and len(alias) > 0:
            return alias
        elif isinstance(model, Model):
            return model.__name__

        return None

    # final method; please do not override
    @classmethod
    def hasOne(cls, field=None, model=None, to=None, alias=None, **kwargs):
        debug(
            "%s.hasOne(field: %s, model: %s, to: %s, alias: %s) called..."
            % (cls.__name__, field, model, to, alias),
            level=1,
        )

        name = cls.__joinFieldName(field=field, model=model, to=to, alias=alias)
        if name:
            if name in cls._relationships:
                raise RuntimeError(
                    "Cannot initialize model relationship '%s' as a relationship with the same name already exists! Use aliases if necessary to distinguish the relationships."
                    % (name)
                )
            else:
                cls._relationships[name] = {
                    "type": "hasOne",
                    "named": name,
                    "field": field,
                    "model": model,
                    "to": to,
                    "alias": alias,
                    "kwargs": kwargs,
                }

    # final method; please do not override
    @classmethod
    def hasMany(cls, field=None, model=None, to=None, alias=None, **kwargs):
        debug(
            "%s.hasMany(field: %s, model: %s, to: %s, alias: %s) called..."
            % (cls.__name__, field, model, to, alias),
            level=1,
        )

        name = cls.__joinFieldName(field=field, model=model, to=to, alias=alias)
        if name:
            if name in cls._relationships:
                raise RuntimeError(
                    "Cannot initialize model relationship '%s' as a relationship with the same name already exists! Use aliases if necessary to distinguish the relationships."
                    % (name)
                )
            else:
                cls._relationships[name] = {
                    "type": "hasMany",
                    "named": name,
                    "field": field,
                    "model": model,
                    "to": to,
                    "alias": alias,
                    "kwargs": kwargs,
                }

    # final method; please do not override
    @classmethod
    def hasManyToMany(cls, field=None, model=None, to=None, alias=None, **kwargs):
        debug(
            "%s.hasManyToMany(field: %s, model: %s, to: %s, alias: %s) called..."
            % (cls.__name__, field, model, to, alias),
            level=1,
        )

        name = cls.__joinFieldName(field=field, model=model, to=to, alias=alias)
        if name:
            if name in cls._relationships:
                raise RuntimeError(
                    "Cannot initialize model relationship '%s' as a relationship with the same name already exists! Use aliases if necessary to distinguish the relationships."
                    % (name)
                )
            else:
                cls._relationships[name] = {
                    "type": "hasManyToMany",
                    "named": name,
                    "field": field,
                    "model": model,
                    "to": to,
                    "alias": alias,
                    "kwargs": kwargs,
                }

    # final method; please do not override
    @classmethod
    def belongsTo(cls, field=None, model=None, to=None, alias=None, **kwargs):
        debug(
            "%s.belongsTo(field: %s, model: %s, to: %s, alias: %s) called..."
            % (cls.__name__, field, model, to, alias),
            level=1,
        )

        name = cls.__joinFieldName(field=field, model=model, to=to, alias=alias)
        if name:
            if name in cls._relationships:
                raise RuntimeError(
                    "Cannot initialize model relationship '%s' as a relationship with the same name already exists! Use aliases if necessary to distinguish the relationships."
                    % (name)
                )
            else:
                cls._relationships[name] = {
                    "type": "belongsTo",
                    "named": name,
                    "field": field,
                    "model": model,
                    "to": to,
                    "alias": alias,
                    "kwargs": kwargs,
                }

    @classmethod
    def count(cls, *args, **kwargs):
        debug(
            "%s.count(args: %s, kwargs: %s) called..." % (cls.__name__, args, kwargs),
            level=1,
        )

        records = None

        clause = None
        if "clause" in kwargs:
            if isinstance(kwargs["clause"], str) and len(kwargs["clause"]) > 0:
                clause = kwargs["clause"]
            del kwargs["clause"]
        elif args and args[0] and isinstance(args[0], str) and len(args[0]) > 0:
            clause = args[0]

        params = None
        if "bind" in kwargs:
            if isinstance(kwargs["bind"], dict):
                params = kwargs["bind"]
            elif isinstance(kwargs["bind"], list):
                params = kwargs["bind"]

        query = cls.prepareQuery("count", clause=clause, params=params, **kwargs)
        if query:
            results = cls.performQuery(query)
            if isinstance(results, list) and len(results) > 0 and results[0]:
                result = results[0]
                if result:
                    return result[0]

        return None

    @classmethod
    def find(cls, *args, **kwargs):
        debug(
            "%s.find(args: %s, kwargs: %s) called..." % (cls.__name__, args, kwargs),
            level=1,
        )

        records = None

        clause = None
        if "clause" in kwargs:
            if isinstance(kwargs["clause"], str) and len(kwargs["clause"]) > 0:
                clause = kwargs["clause"]
            del kwargs["clause"]
        elif args and args[0] and isinstance(args[0], str) and len(args[0]) > 0:
            clause = args[0]

        params = None
        if "bind" in kwargs:
            if isinstance(kwargs["bind"], dict):
                params = kwargs["bind"]
            elif isinstance(kwargs["bind"], list):
                params = kwargs["bind"]

        query = cls.prepareQuery("find", clause=clause, params=params, **kwargs)
        if query:
            results = cls.performQuery(query)
            if isinstance(results, list) and len(results) > 0:
                records = []

                field = cls.getIDField()

                for result in results:
                    attributes = cls.__attributesFromResult(result)
                    if attributes:
                        if field in attributes:
                            model = cls.getModelClass()
                            if model:
                                instance = model(attributes=attributes)
                                if instance:
                                    instance.__fireEvent(
                                        event="fetch", stage="after", **kwargs
                                    )

                                    records.append(instance)
                                else:
                                    debug(
                                        "%s.find() Failed to instantiate a new %s class instance!"
                                        % (cls.__name__, model),
                                        error=True,
                                    )
                            else:
                                debug(
                                    "%s.find() Failed to determine model class!"
                                    % (cls.__name__),
                                    error=True,
                                )
                        else:
                            debug(
                                "%s.find() Failed to find model ID field within attributes!"
                                % (cls.__name__),
                                error=True,
                            )
                    else:
                        debug(
                            "%s.find() Failed to obtain attributes from result!"
                            % (cls.__name__),
                            error=True,
                        )
            else:
                debug("%s.find() No results were found!" % (cls.__name__), error=True)
        else:
            debug(
                "%s.find() The query could not be prepared!" % (cls.__name__),
                error=True,
            )

        return records

    @classmethod
    def findFirst(cls, *args, **kwargs):
        debug(
            "%s.findFirst(args: %s, kwargs: %s) called..."
            % (cls.__name__, args, kwargs),
            level=1,
        )

        results = None

        if args and len(args) == 1 and isinstance(args[0], int):
            field = cls.getIDField()
            if field:
                results = cls.find(
                    sprintf("%s = :%s:" % (field, field)),
                    bind={field: args[0]},
                    limit=1,
                    **kwargs
                )
        else:
            results = cls.find(*args, limit=1, **kwargs)

        record = None

        if isinstance(results, list) and len(results) > 0:
            if results[0]:
                record = results[0]

        return record

    @classmethod
    def findFirstOrCreateNewInstance(cls, *args, **kwargs):
        debug(
            "%s.findFirstOrCreateNewInstance(args: %s, kwargs: %s) called..."
            % (cls.__name__, args, kwargs),
            level=1,
        )

        record = cls.findFirst(*args, **kwargs)
        if record:
            return record
        else:
            return cls()

    # final method; please do not override
    @classmethod
    def __attributesFromResult(cls, result):
        if result:
            dictionary = {}

            for key in dir(result):
                if not key.startswith("_"):
                    value = getattr(result, key)
                    if value:
                        if not callable(value):
                            # debug(" - %s => %s (%s)" % (key, value, type(value)))

                            if isinstance(value, datetime):
                                value = value.strftime("%Y-%m-%d %H:%M:%S%z")

                            dictionary[key] = value

            return dictionary

        return None

    # final method; please do not override
    def isNew(self):
        """Determine if the instance is new or not"""

        field = self.getIDField()
        if isinstance(field, str):
            id = getattr(self, field)
            if id:
                return False

        return True

    # final method; please do not override
    def save(self, **kwargs):
        debug("%s.save(%s) called..." % (self.__class__.__name__, kwargs), level=1)

        result = None

        if self.__fireEvent(event="save", stage="before", **kwargs):
            if self.id:
                result = self.update(**kwargs)
            else:
                result = self.create(**kwargs)

            self.__fireEvent(event="save", stage="after", **kwargs)

        return result

    # final method; please do not override
    def create(self, **kwargs):
        debug("%s.create(%s) called..." % (self.__class__.__name__, kwargs), level=1)

        result = None

        if self.__fireEvent(event="create", stage="before", **kwargs):
            attributes = self.getAttributeValues()

            query = self.prepareQuery(
                "create", id=self.id, params=attributes, self=self
            )
            if query:
                id = self.performQuery(query)
                if id:
                    self.id = id

                    result = True

                    self.__fireEvent(event="create", stage="after", **kwargs)
                else:
                    debug("Failed to create the record!", error=True)

        return result

    # final method; please do not override
    def update(self, **kwargs):
        debug("%s.update(%s) called..." % (self.__class__.__name__, kwargs), level=1)

        result = None

        if self.__fireEvent(event="update", stage="before", **kwargs):
            # only save the record if something has changed or a force update is made
            if self.hasChanged() or ("force" in kwargs and kwargs["force"] == True):
                attributes = self.getAttributeValues()

                query = self.prepareQuery(
                    "update", id=self.id, params=attributes, self=self
                )
                if query:
                    result = self.performQuery(query)
                    if result:
                        result = True
            else:
                debug(
                    "%s.update(%s) Apparently %s has not changed?"
                    % (self.__class__.__name__, kwargs, self),
                    level=1,
                    error=True,
                )

                result = True

            self.__fireEvent(event="update", stage="after", **kwargs)

        return result

    # final method; please do not override
    def delete(self, **kwargs):
        debug("%s.delete(%s) called..." % (self.__class__.__name__, kwargs), level=1)

        result = None

        if self.__fireEvent(event="delete", stage="before", **kwargs):
            query = self.prepareQuery("delete", id=self.id, self=self)
            if query:
                result = self.performQuery(query)
                if result:
                    result = True

                self.__fireEvent(event="delete", stage="after", **kwargs)

        return result

    # final method; please do not override
    @classmethod
    def autoPopulatedFields(cls, fields):
        debug("%s.autoPopulatedFields() called..." % (cls.__name__), level=1)

        if isinstance(fields, list) and len(fields) > 0:
            cls._autopopulated = fields

    def changedFields(self):
        debug("%s.changedFields() called..." % (self.__class__.__name__), level=1)

        changed = {}

        attributes = self.getAttributeValues()
        if isinstance(attributes, dict) and len(attributes) > 0:
            for attribute in attributes:
                debug(
                    "attribute = %s (snapshot: %s)"
                    % (attribute, (attribute in self._snapshot)),
                    indent=1,
                    level=3,
                )

                if (not (attribute in self._snapshot)) or (
                    not (self._snapshot[attribute] == attributes[attribute])
                ):
                    if attribute in self._snapshot:
                        debug(
                            "attribute = %s (snapshot: %s)"
                            % (attributes[attribute], self._snapshot[attribute]),
                            indent=2,
                            level=3,
                        )

                    if (
                        isinstance(self._autopopulated, list)
                        and attribute in self._autopopulated
                    ):
                        debug(
                            "%s.changedFields() Ignoring changed attribute (%s) as it is an autopopulated field..."
                            % (self.__class__.__name__, attribute),
                            level=2,
                        )
                    else:
                        changed[attribute] = attributes[attribute]

        debug(
            "%s.changedFields() changed = %s" % (self.__class__.__name__, changed),
            level=2,
        )

        if len(changed) > 0:
            return changed

        return None

    def hasChanged(self):
        debug("%s.hasChanged() called..." % (self.__class__.__name__), level=1)

        changed = self.changedFields()
        if isinstance(changed, dict) and len(changed) > 0:
            return True

        return False

    # final method; please do not override
    def __fireEvent(self, event=None, stage=None, **kwargs):
        debug(
            "%s.__fireEvent(event: %s, stage: %s, kwargs: %s) called..."
            % (self.__class__.__name__, event, stage, kwargs),
            level=1,
        )

        result = None

        if not (("quietly" in kwargs) and kwargs["quietly"] == True):
            self.__syncRelated(event=event, stage=stage)

        if stage == "before":
            # call the beforeChange() method
            self.beforeChange(event)

            # call the relevant before method
            if isinstance(event, str) and event in [
                "create",
                "update",
                "save",
                "delete",
            ]:
                beforeMethod = getattr(self, sprintf("before%s" % (event.capitalize())))
                if callable(beforeMethod):
                    result = beforeMethod()
        elif stage == "after":
            # If quiet mode is enabled, return immediately, skipping the post event method calls
            if ("quietly" in kwargs) and kwargs["quietly"] == True:
                return

            if isinstance(event, str) and event not in ["fetch"]:
                # clear any cached related entities
                self._related = {}

                # call the afterChange() method
                self.afterChange(event)

            # call the relevant after method
            if event in ["fetch", "create", "update", "save", "delete"]:
                afterMethod = getattr(self, sprintf("after%s" % (event.capitalize())))
                if callable(afterMethod):
                    afterMethod()

        return result

    # final method; please do not override
    def __getRelated(self, relationship):
        debug(
            "%s.__getRelated(relationship: %s) called..."
            % (self.__class__.__name__, relationship),
            level=1,
        )

        result = None

        if isinstance(relationship, dict):
            type = get(relationship, "type")
            named = get(relationship, "named")
            field = get(relationship, "field")
            model = get(relationship, "model")
            to = get(relationship, "to")
            alias = get(relationship, "alias")
            kwargs = get(relationship, "kwargs")

            if issubclass(model, Model):
                if field:
                    id = getattr(self, field)
                    if id:
                        # build a key from the field and value
                        key = sprintf("%s/%s/%s" % (field, model.__name__, id))
                        if key:
                            # if the key already exists
                            if key in self._related:
                                if isinstance(self._related[key], dict) and (
                                    "value" in self._related[key]
                                ):
                                    if (
                                        "saved" in self._related[key]
                                    ) and self._related[key]["saved"] == True:
                                        # return the cached related result
                                        return self._related[key]["value"]

                            if type == "hasOne":
                                if value:
                                    result = model.findFirst(
                                        sprintf("%s = :%s:" % (to, to)),
                                        bind={to: id},
                                        **kwargs
                                    )
                            elif type == "hasMany":
                                value = getattr(self, field)
                                if value:
                                    result = model.find(
                                        sprintf("%s = :%s:" % (to, to)),
                                        bind={to: id},
                                        **kwargs
                                    )
                            elif type == "hasManyToMany":
                                pass
                            elif type == "belongsTo":
                                value = getattr(self, field)
                                if value:
                                    result = model.findFirst(
                                        sprintf("%s = :%s:" % (to, to)),
                                        bind={to: id},
                                        **kwargs
                                    )
                            else:
                                debug(
                                    "%s.__getRelated(relationship: %s) Unsupported relationship type: %s!"
                                    % (self.__class__.__name__, relationship, type),
                                    level=1,
                                )

                            # if a result was found
                            if result:
                                # cache it to reduce unnecessary database lookups
                                self._related[key] = {
                                    "named": named,
                                    "saved": True,
                                    "value": result,
                                }
                            else:
                                debug(
                                    "%s.__getRelated(relationship: %s) No result could not be defined!"
                                    % (self.__class__.__name__, relationship),
                                    level=1,
                                )
                        else:
                            debug(
                                "%s.__getRelated(relationship: %s) The relationship key could not be defined!"
                                % (self.__class__.__name__, relationship),
                                level=1,
                            )
                    else:
                        debug(
                            "%s.__getRelated(relationship: %s) The foreign key ID could not be obtained!"
                            % (self.__class__.__name__, relationship),
                            level=1,
                        )
                else:
                    debug(
                        "%s.__getRelated(relationship: %s) The primary key field was not specified!"
                        % (self.__class__.__name__, relationship),
                        level=1,
                    )
            else:
                debug(
                    "%s.__getRelated(relationship: %s) The model is not a subclass of Model!"
                    % (self.__class__.__name__, relationship),
                    level=1,
                )
        else:
            debug(
                "%s.__getRelated(relationship: %s) The relationship was not defined as a dictionary!"
                % (self.__class__.__name__, relationship),
                level=1,
            )

        return result

    # final method; please do not override
    def __setRelated(self, relationship, value):
        debug(
            "%s.__setRelated(relationship: %s, value: %s) called..."
            % (self.__class__.__name__, relationship, value),
            level=1,
        )

        result = None

        if isinstance(relationship, dict):
            type = get(relationship, "type")
            named = get(relationship, "named")
            field = get(relationship, "field")
            model = get(relationship, "model")
            to = get(relationship, "to")
            alias = get(relationship, "alias")
            kwargs = get(relationship, "kwargs")

            if model:
                if isinstance(value, model):
                    id = value.getID()
                    if id:
                        # build a key from the field and value
                        key = sprintf("%s/%s/%s" % (field, model.__name__, id))

                        if key:
                            self._related[key] = {
                                "named": named,
                                "saved": False,
                                "value": value,
                            }
                    else:
                        debug(
                            "%s.__setRelated(relationship: %s, value: %s) Provided model instance has no valid ID!"
                            % (self.__class__.__name__, relationship, value, model),
                            error=True,
                        )
                else:
                    debug(
                        "%s.__setRelated(relationship: %s, value: %s) Provided model instance is not an instance of %s!"
                        % (self.__class__.__name__, relationship, value, model),
                        error=True,
                    )
            else:
                debug(
                    "%s.__setRelated(relationship: %s, value: %s) Related model (%s) is not an instance of %s!"
                    % (self.__class__.__name__, relationship, value, model, Model),
                    error=True,
                )

    # final method; please do not override
    def __syncRelated(self, event=None, stage=None):
        debug(
            "%s.__syncRelated(event: %s, stage: %s) called..."
            % (self.__class__.__name__, event, stage),
            level=1,
        )

        relationships = self.__class__._relationships
        if isinstance(relationships, dict) and len(relationships) > 0:
            if isinstance(self._related, dict) and len(self._related) > 0:
                debug(
                    "Found %d related items" % (len(self._related)), indent=1, level=2
                )

                changed = False

                for key in self._related:
                    related = self._related[key]
                    if isinstance(related, dict):
                        if get(related, "saved") == False:
                            debug("Need to save related: %s" % (key), indent=2, level=3)

                            named = get(related, "named")
                            if named:
                                if named in relationships:
                                    relationship = relationships[named]
                                    if isinstance(relationship, dict):
                                        # debug(relationship)

                                        type = get(relationship, "type")
                                        named = get(relationship, "named")
                                        field = get(relationship, "field")
                                        model = get(relationship, "model")
                                        to = get(relationship, "to")
                                        alias = get(relationship, "alias")
                                        kwargs = get(relationship, "kwargs")

                                        value = get(related, "value")
                                        if isinstance(value, model):
                                            if to:
                                                id = getattr(value, to)
                                                if id:
                                                    if stage == "before":
                                                        if type == "hasOne":
                                                            setattr(self, field, id)
                                                            changed = True
                                                        elif type == "belongsTo":
                                                            setattr(self, field, id)
                                                            changed = True
                                                        elif type == "hasMany":
                                                            pass
                                                        elif type == "hasManyToMany":
                                                            pass
                                                    elif stage == "after":
                                                        if type == "hasOne":
                                                            setattr(self, field, id)
                                                            changed = True
                                                        elif type == "belongsTo":
                                                            setattr(self, field, id)
                                                            changed = True
                                                        elif type == "hasMany":
                                                            pass
                                                        elif type == "hasManyToMany":
                                                            pass

                if stage == "after" and event not in ["fetch"]:
                    if changed:
                        # save any changes, but do so quietly, to avoid firing the
                        # after events again and thus ending up in an endless loop

                        self.save(quietly=True)

    def beforeChange(self, event):
        debug(
            "%s.beforeChange(event: %s) called..." % (self.__class__.__name__, event),
            level=1,
        )
        return True

    def beforeSave(self):
        debug("%s.beforeSave() called..." % (self.__class__.__name__), level=1)
        return True

    def beforeCreate(self):
        debug("%s.beforeCreate() called..." % (self.__class__.__name__), level=1)
        return True

    def beforeUpdate(self):
        debug("%s.beforeUpdate() called..." % (self.__class__.__name__), level=1)
        return True

    def beforeDelete(self):
        debug("%s.beforeDelete() called..." % (self.__class__.__name__), level=1)
        return True

    def afterFetch(self):
        debug("%s.afterFetch() called..." % (self.__class__.__name__), level=1)
        pass

    def afterChange(self, event):
        debug(
            "%s.afterChange(event: %s) called..." % (self.__class__.__name__, event),
            level=1,
        )
        pass

    def afterSave(self):
        debug("%s.afterSave() called..." % (self.__class__.__name__), level=1)
        pass

    def afterCreate(self):
        debug("%s.afterCreate() called..." % (self.__class__.__name__), level=1)
        pass

    def afterUpdate(self):
        debug("%s.afterUpdate() called..." % (self.__class__.__name__), level=1)
        pass

    def afterDelete(self):
        debug("%s.afterDelete() called..." % (self.__class__.__name__), level=1)
        pass

    # final method; please do not override
    def getAttributes(self, includePrivate=False):
        debug(
            "%s.getAttributes(includePrivate: %s) called..."
            % (self.__class__.__name__, includePrivate),
            level=1,
        )

        attributes = []

        for attribute in self.__dict__.keys():
            if isinstance(attribute, str):
                if includePrivate == True or not attribute.startswith("_"):
                    attributes.append(attribute)

        return attributes

    # final method; please do not override
    def getAttributeValues(self):
        debug("%s.getAttributeValues() called..." % (self.__class__.__name__), level=1)

        values = {}

        for attribute in self.getAttributes():
            values[attribute] = getattr(self, attribute)

        if len(values) > 0:
            return values

        return None

    # final method; please do not override
    @classmethod
    def getClassAttributes(cls):
        debug("%s.getClassAttributes() called..." % (cls.__name__), level=1)

        attributes = []

        import inspect

        members = inspect.getmembers(cls)
        if members:
            for member in members:
                if member[0]:
                    if not member[0].startswith("_"):
                        attr = getattr(cls, member[0])
                        if not callable(attr):
                            attributes.append(member[0])

            if len(attributes) > 0:
                return attributes

        return None

    # final method; please do not override
    @classmethod
    def getClassAttributeValues(cls):
        debug("%s.getClassAttributeValues() called..." % (cls.__name__), level=1)

        attributes = {}

        import inspect

        members = inspect.getmembers(cls)
        if members:
            for member in members:
                if member[0]:
                    if not member[0].startswith("_"):
                        attr = getattr(cls, member[0])
                        if not callable(attr):
                            attributes[member[0]] = member[1]

            if len(attributes) > 0:
                return attributes

        return None

    # final method; please do not override
    @classmethod
    def prepareQuery(cls, event, id=None, params=None, self=None, **kwargs):
        debug(
            "%s.prepareQuery(event: %s, id: %s, params: %s, kwargs: %s) called..."
            % (cls.__name__, event, id, params, kwargs),
            level=1,
        )

        table = cls.getSource()
        field = cls.getIDField()
        query = None
        limit = None
        values = None

        attributes = cls.getClassAttributes()
        if attributes:
            # debug(attributes, format="JSON", level=2)

            action = None
            if event in ["save", "create", "update"]:
                if id:
                    action = "UPDATE"
                else:
                    action = "INSERT"
            elif event == "delete":
                action = "DELETE"
            elif event == "find" or event == "count":
                action = "SELECT"

            if ("limit" in kwargs) and isinstance(kwargs["limit"], int):
                limit = kwargs["limit"]

            if action:
                if action == "INSERT":
                    if isinstance(params, dict):
                        count = len(params)
                        if count > 0:
                            values = []
                            query = "INSERT INTO " + table + " ("

                            index = 0
                            for attribute in attributes:
                                if attribute in params:
                                    query += attribute

                                    index += 1

                                    values.append(params[attribute])

                                    if index < count:
                                        query += ", "

                            query += ") VALUES ("

                            index = 0
                            for attribute in attributes:
                                if attribute in params:
                                    query += "%s"

                                    index += 1

                                    if index < count:
                                        query += ", "

                            query += ")"

                            if isinstance(field, str) and len(field) > 0:
                                query += " RETURNING " + field
                elif action == "UPDATE":
                    if isinstance(params, dict) and len(params) > 0:
                        changed = {}
                        for attribute in attributes:
                            if attribute in params:
                                if not (
                                    attribute in self._snapshot
                                    and self._snapshot[attribute] == params[attribute]
                                ):
                                    changed[attribute] = params[attribute]

                        # debug(self._snapshot, label="snapshot", format="JSON")
                        # debug(changed, label="changed", format="JSON")
                        # debug(params, label="params", format="JSON")

                        count = len(changed)
                        if count > 0:
                            values = []
                            query = "UPDATE " + table + " SET "

                            index = 0
                            for attribute in attributes:
                                if attribute in changed:
                                    query += attribute + " = %s"

                                    index += 1

                                    values.append(changed[attribute])

                                    if index < count:
                                        query += ", "

                            if len(values) > 0:
                                query += " WHERE " + field + " = %s"
                                values.append(id)
                            else:
                                query = None
                                values = None
                elif action == "DELETE":
                    query = "DELETE FROM " + table + " WHERE id = %s"

                    if id:
                        values = [id]
                elif action == "SELECT":
                    if event == "count":
                        query = "SELECT COUNT(" + field + ") AS counter FROM " + table
                    else:
                        query = "SELECT * FROM " + table

                    if id:
                        query += " WHERE " + field + " = %s"
                        values = [id]
                    elif "clause" in kwargs:
                        if isinstance(kwargs["clause"], str):
                            clause = kwargs["clause"]
                            if len(clause) > 0:
                                values = []
                                valid = True
                                index = 0

                                if clause.find(":") > 0:

                                    def clauseParam(match):
                                        nonlocal valid, params

                                        # debug("clauseParam() called... valid = %s" % (valid))

                                        param = match.group(1)

                                        if isinstance(params, dict):
                                            if param in params:
                                                values.append(params[param])

                                                return "%s"
                                            else:
                                                debug(
                                                    "%s.prepareQuery() Unable to find param[%s]!"
                                                    % (cls.__name__, param),
                                                    error=True,
                                                )

                                                valid = False

                                                return ":" + param + ":"
                                        else:
                                            debug(
                                                "%s.prepareQuery() The provided params were invalid! Expected a dictionary, instead found %s"
                                                % (cls.__name__, type(params)),
                                                error=True,
                                            )

                                            valid = False

                                            return ":" + param + ":"

                                    clause = re.sub(
                                        r"\:([a-z\_]{1}[a-z0-9\_]+)\:",
                                        clauseParam,
                                        clause,
                                        flags=re.IGNORECASE,
                                    )
                                elif clause.find("?") > 0:

                                    def clauseParam(match):
                                        nonlocal valid, index, params

                                        # debug("clauseParam() called... valid = %s, index = %s" % (valid, index))

                                        param = match.group(1)

                                        if isinstance(params, list):
                                            if index < len(params):
                                                values.append(params[index])

                                                index += 1

                                                return "%s"
                                            else:
                                                debug(
                                                    "%s.prepareQuery() Unable to find param[%s]!"
                                                    % (cls.__name__, index),
                                                    error=True,
                                                )

                                                valid = False

                                                return param
                                        else:
                                            debug(
                                                "%s.prepareQuery() The provided params were invalid! Expected a list, instead found %s"
                                                % (cls.__name__, type(params)),
                                                error=True,
                                            )
                                            valid = False

                                            return param

                                    clause = re.sub(
                                        r"(?<=\s{1})(\?)",
                                        clauseParam,
                                        clause,
                                        flags=re.IGNORECASE,
                                    )

                                # debug(clause, valid)

                                query += " WHERE " + clause

                                if valid == False:
                                    debug(
                                        "%s.prepareQuery() Failed to replace all clause (%s) placeholders!"
                                        % (cls.__name__, clause),
                                        error=True,
                                    )

                                    raise RuntimeError(
                                        sprintf(
                                            "%s.prepareQuery() Failed to replace all clause (%s) placeholders!"
                                            % (cls.__name__, clause)
                                        )
                                    )

                                    return False

                                del valid, index

                    if query:
                        if "grouping" in kwargs:
                            if isinstance(kwargs["grouping"], str):
                                grouping = kwargs["grouping"]
                                if len(grouping) > 0:
                                    query += " GROUP BY " + grouping

                        if "having" in kwargs:
                            if isinstance(kwargs["having"], str):
                                having = kwargs["having"]
                                if len(having) > 0:
                                    query += " HAVING " + having

                        if "ordering" in kwargs:
                            if isinstance(kwargs["ordering"], str):
                                ordering = kwargs["ordering"]
                                if len(ordering) > 0:
                                    query += " ORDER BY " + ordering
                            elif isinstance(kwargs["ordering"], list):
                                ordering = kwargs["ordering"]
                                for index, order in enumerate(ordering):
                                    if isinstance(order, str) and len(order) > 0:
                                        if index == 0:
                                            query += " ORDER BY " + order
                                        else:
                                            query += ", " + order
                            elif isinstance(kwargs["ordering"], dict):
                                ordering = kwargs["ordering"]
                                for index, key in enumerate(ordering):
                                    order = ordering[key]

                                    if isinstance(order, str):
                                        if index == 0:
                                            query += " ORDER BY " + key + " " + order
                                        else:
                                            query += ", " + key + " " + order

                        if limit:
                            if isinstance(limit, int):
                                if limit > 0:
                                    query += " LIMIT " + str(limit)

                        if "offset" in kwargs:
                            if isinstance(kwargs["offset"], int):
                                offset = kwargs["offset"]
                                if offset > 0:
                                    query += " OFFSET " + str(offset)
            else:
                pass

        if action and table and query:
            return {
                "action": action,
                "table": table,
                "string": query,
                "values": values,
                "limit": limit,
                "field": field,
            }

        return None

    # final method; please do not override
    @classmethod
    def performQuery(cls, query):
        debug("%s.performQuery(query: %s) called..." % (cls.__name__, query), level=1)

        result = None

        database = DI.get("database")
        if not database:
            raise RuntimeError("No database handler could be found!")

        connection = DI.get("connection")
        if not connection:
            raise RuntimeError("No database connection could be found!")

        debug(
            "Successfully obtained database service: %s and connection: %s"
            % (database, connection),
            level=2,
        )

        if isinstance(query, dict):
            if "action" in query:
                action = query["action"]
                if isinstance(action, str) and action in [
                    "SELECT",
                    "INSERT",
                    "UPDATE",
                    "DELETE",
                ]:
                    if "string" in query:
                        if (
                            isinstance(query["string"], str)
                            and len(query["string"]) > 0
                        ):
                            if query["string"].startswith(action):
                                string = query["string"]

                                cursor = database.cursor(connection=connection)
                                if cursor:
                                    try:

                                        debug(query, format="JSON", level=3)

                                        values = []

                                        if "values" in query:
                                            if isinstance(query["values"], list):
                                                values = query["values"]

                                        # SELECT * FROM records WHERE record_id = %s AND type = %s

                                        # 	if(isinstance(query["values"], dict)):
                                        # 		for key in query["values"]:
                                        # 			params.append(query["values"][key])

                                        # debug(values, format="JSON", level=3)

                                        try:
                                            # TODO Is there a better way to resolve the transaction issue?
                                            database.commit(connection=connection)
                                        except:
                                            pass

                                        cursor.execute(string, values)

                                        debug(
                                            " >>> query.string    = %s" % (string),
                                            level=3,
                                        )
                                        debug(
                                            " >>> cursor.rowcount = %s"
                                            % (cursor.rowcount),
                                            level=3,
                                        )
                                        debug(
                                            " >>> cursor type     = %s" % type(cursor),
                                            level=3,
                                        )

                                        if action == "SELECT":
                                            if (
                                                ("limit" in query)
                                                and isinstance(query["limit"], int)
                                                and query["limit"] == 1
                                            ):
                                                results = cursor.fetchone()
                                                if results:
                                                    results = [results]
                                            else:
                                                results = cursor.fetchall()

                                            if results:
                                                result = results
                                        else:
                                            if cursor.rowcount > 0:
                                                if action == "INSERT":
                                                    if "field" in query:
                                                        field = query["field"]
                                                        if isinstance(field, str):
                                                            id = get(
                                                                cursor.fetchone(), [0]
                                                            )
                                                            if id:
                                                                result = id
                                                            else:
                                                                result = False
                                                        else:
                                                            result = True
                                                    else:
                                                        result = True
                                                elif action in ["UPDATE", "DELETE"]:
                                                    result = True
                                            else:
                                                result = False

                                        if action == "SELECT":
                                            database.commit(connection=connection)
                                        else:
                                            if connection.autocommit == True:
                                                debug(
                                                    "%s.performQuery() Committing changes to database automatically as per configuration..."
                                                    % (cls.__name__),
                                                    level=1,
                                                )

                                                database.commit(connection=connection)
                                            else:
                                                debug(
                                                    "%s.performQuery() Not committing changes to database automatically as per configuration..."
                                                    % (cls.__name__),
                                                    level=1,
                                                )
                                    except Exception as e:
                                        debug(
                                            "%s.performQuery() An exception occurred while trying to perform the query!"
                                            % (cls.__name__),
                                            error=True,
                                        )
                                        debug(e)

                                        database.rollback(connection=connection)

                                    cursor.close()
                                else:
                                    debug(
                                        "%s.performQuery() Failed to obtain database cursor!"
                                        % (cls.__name__),
                                        error=True,
                                    )
                            else:
                                debug(
                                    "%s.performQuery() The provided query string (%s) does not begin with the expected action: %s!"
                                    % (cls.__name__, string, action),
                                    error=True,
                                )
                        else:
                            debug(
                                "%s.performQuery() The provided query string was not a string, but rather of type: %s!"
                                % (cls.__name__, type(string)),
                                error=True,
                            )
                    else:
                        debug(
                            "%s.performQuery() No query string was provided!"
                            % (cls.__name__),
                            error=True,
                        )
                else:
                    debug(
                        "%s.performQuery() The provided query action (%s) was invalid!"
                        % (cls.__name__, action),
                        error=True,
                    )
            else:
                debug(
                    "%s.performQuery() No query action was provided!" % (cls.__name__),
                    error=True,
                )
        else:
            debug(
                "%s.performQuery() The query was invalid! It should be a dictionary!"
                % (cls.__name__),
                error=True,
            )

        return result

    @classmethod
    def commit(cls):
        debug("%s.commit() called..." % (cls.__name__), level=1)

        database = DI.get("database")
        if not database:
            raise RuntimeError("No database handler could be found!")

        connection = DI.get("connection")
        if not connection:
            raise RuntimeError("No database connection could be found!")

        debug(
            "Successfully obtained database service: %s and connection: %s"
            % (database, connection),
            level=2,
        )

        if connection.autocommit == False:
            if isinstance(database, Database):
                database.commit(connection=connection)

    @classmethod
    def rollback(cls):
        debug("%s.rollback() called..." % (cls.__name__), level=1)

        database = DI.get("database")
        if not database:
            raise RuntimeError("No database handler could be found!")

        connection = DI.get("connection")
        if not connection:
            raise RuntimeError("No database connection could be found!")

        debug(
            "Successfully obtained database service: %s and connection: %s"
            % (database, connection),
            level=2,
        )

        if connection.autocommit == False:
            if isinstance(database, Database):
                database.rollback(connection=connection)


class Activity(Model):

    id = None
    datetime_created = None
    datetime_updated = None
    datetime_started = None
    datetime_ended = None
    datetime_published = None
    uuid = None
    event = None
    namespace = None
    entity = None
    record_id = None

    @classmethod
    def getSource(cls):
        return "activities"

    @classmethod
    def initialize(cls):
        debug("%s.initialize() called..." % (cls.__name__), level=1)

        # Note any fields populated automatically by the model instance
        cls.autoPopulatedFields(["datetime_created", "datetime_updated", "uuid"])

        # Establish the Record join
        cls.belongsTo(field="record_id", model=Record, to="id", alias="record")

    def beforeCreate(self):
        debug("%s.beforeCreate() called..." % (self.__class__.__name__), level=1)

        self.datetime_created = date(format="%Y-%m-%d %H:%M:%S%z")
        self.uuid = str(uuid.uuid4())

        return True

    def beforeUpdate(self):
        debug("%s.beforeUpdate() called..." % (self.__class__.__name__), level=1)

        self.datetime_updated = date(format="%Y-%m-%d %H:%M:%S%z")

        return True

    def beforeSave(self):
        debug("%s.beforeSave() called..." % (self.__class__.__name__), level=1)

        return True


class Record(Model):

    id = None
    datetime_created = None
    datetime_updated = None
    datetime_published = None
    uuid = None
    namespace = None
    entity = None
    data = None
    attributes = None
    counter = None

    @classmethod
    def getSource(cls):
        return "records"

    @classmethod
    def initialize(cls):
        debug("%s.initialize() called..." % (cls.__name__), level=1)

        # Note any fields populated automatically by the model instance
        cls.autoPopulatedFields(["datetime_created", "datetime_updated"])

        # Establish the Activity join
        cls.hasMany(field="id", model=Activity, to="record_id", alias="activities")

    def beforeCreate(self):
        debug("%s.beforeCreate() called..." % (self.__class__.__name__), level=1)

        self.datetime_created = date(format="%Y-%m-%d %H:%M:%S%z")

        return True

    def beforeUpdate(self):
        debug("%s.beforeUpdate() called..." % (self.__class__.__name__), level=1)

        self.datetime_updated = date(format="%Y-%m-%d %H:%M:%S%z")

        return True

    def beforeSave(self):
        debug("%s.beforeSave() called..." % (self.__class__.__name__), level=1)
        return True

    def afterFetch(self):
        debug("%s.afterFetch() called..." % (self.__class__.__name__), level=1)

    def afterChange(self, event):
        debug(
            "%s.afterChange(event: %s) called..." % (self.__class__.__name__, event),
            level=1,
        )

        if event in ["create", "update", "delete"]:
            activity = Activity()
            if activity:
                activity.event = event.capitalize()
                activity.namespace = self.namespace
                activity.entity = self.entity
                activity.record = self

                if activity.save():
                    debug("Successfully saved %s" % (activity))
                else:
                    debug("Failed to save %s!" % (activity), error=True)

    def afterCreate(self):
        debug("%s.afterCreate() called..." % (self.__class__.__name__), level=1)

    def afterUpdate(self):
        debug("%s.afterUpdate() called..." % (self.__class__.__name__), level=1)

    def afterDelete(self):
        debug("%s.afterDelete() called..." % (self.__class__.__name__), level=1)


class Stream(Model):

    id = None
    datetime_created = None
    datetime_updated = None
    namespace = None
    base_url = None
    last_id = None

    @classmethod
    def getSource(cls):
        return "streams"

    @classmethod
    def initialize(cls):
        debug("%s.initialize() called..." % (cls.__name__), level=1)

        # Note any fields populated automatically by the model instance
        cls.autoPopulatedFields(["datetime_created", "datetime_updated"])

    def beforeCreate(self):
        debug("%s.beforeCreate() called..." % (self.__class__.__name__), level=1)

        self.datetime_created = date(format="%Y-%m-%d %H:%M:%S%z")

        return True

    def beforeUpdate(self):
        debug("%s.beforeUpdate() called..." % (self.__class__.__name__), level=1)

        self.datetime_updated = date(format="%Y-%m-%d %H:%M:%S%z")

        return True

    def beforeSave(self):
        debug("%s.beforeSave() called..." % (self.__class__.__name__), level=1)

        return True
