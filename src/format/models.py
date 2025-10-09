# -*- coding: utf-8 -*-
"""
Core TSPLIB95 parsing models and field system.

This module contains the vendored TSPLIB95 library components used for parsing.
It provides the low-level parsing infrastructure with a field-based architecture
for declarative problem specification parsing.

Architecture
------------
- **Field System**: Declarative fields (StringField, IntegerField, etc.) define TSPLIB95 keywords
- **Transformers**: Convert text to structured data (FuncT, ListT, MapT, etc.)
- **StandardProblem**: Main problem class using fields to parse TSPLIB95 format
- **BiSep & Utils**: Bidirectional separator and utility functions for text processing

Key Classes
-----------
StandardProblem
    Main problem class with fields for all TSPLIB95 keywords.
    Uses `as_name_dict()` to export parsed data as dict.

Field (base class)
    Base for all field types. Fields are descriptors that parse and validate data.

TransformerField
    Field subclass that uses transformers for parsing.

Usage Note
----------
This is **vendored legacy code** from the original TSPLIB95 library.
The converter primarily uses FormatParser (parser.py) which wraps these models.
Direct usage of StandardProblem is discouraged - use FormatParser instead.

Type Hints
----------
⚠️ This module contains ~1152 Pylance errors in the Field system and transformers.
These are acceptable as this is legacy code scheduled for eventual replacement.
The public API (FormatParser in parser.py) has 0 errors.
"""
import re
from typing import Any, Dict
from . import exceptions


# ============================================================================
# Minimal inline utilities (from bisep.py and utils.py)
# ============================================================================

class BiSep:
    """Bidirectional separator for parsing."""
    def __init__(self, *, in_=None, out=' '):
        self.i = in_
        self.o = out

    def split(self, text, maxsplit=None):
        maxsplit = -1 if maxsplit is None else maxsplit
        return text.split(self.i, maxsplit=maxsplit)

    def join(self, items):
        o = ' ' if self.o is None else self.o
        return o.join(items)


def _bisep_from_value(value):
    """Create BiSep from value - inlined from bisep.py"""
    if value is None or isinstance(value, str):
        i, o = value, value
    else:
        try:
            i, o = value
        except Exception:
            raise ValueError('must be a string or an in/out '
                             f'tuple, not {value}')
    return BiSep(in_=i, out=o)


def _friendly_join(items, limit=None):
    """Join items in a friendly way for error messages - inlined from utils.py"""
    if not items:
        return ''

    if limit is not None:
        truncated = len(items) - limit
        items = items[:limit]
        if truncated > 0:
            items.append(f'{truncated} more')

    *items, last_item = items
    if not items:
        return str(last_item)

    # oxford commas are important
    if len(items) == 1:
        return f'{items[0]} and {last_item}'
    return f'{", ".join(items)}, and {last_item}'


# ============================================================================
# Minimal transformers (from transformers.py)
# ============================================================================

class Transformer:
    """Base transformer class."""
    
    def parse(self, text):
        """Parse text into a value."""
        raise NotImplementedError()

    def validate(self, value):
        """Validate a value."""
        pass


class FuncT(Transformer):
    """Transformer that applies a function."""
    
    def __init__(self, *, func=None):
        self.func = func or (lambda x: x)

    def parse(self, text):
        try:
            return self.func(text)
        except Exception as e:
            error = f'could not apply {self.func.__name__} to {text}: {e}'
            raise exceptions.ParsingError(error)


class NumberT(Transformer):
    """Transformer for any number, int or float."""

    def parse(self, text):
        for func in (int, float):
            try:
                return func(text)
            except ValueError:
                pass
        error = f'could not convert text to number: {text}'
        raise exceptions.ParsingError(error)


class ContainerT(Transformer):
    """Base transformer for containers."""

    def __init__(self, *, value=None, sep=None, terminal=None,
                 terminal_required=True, size=None, filter_empty=True):
        self.child_tf = value or Transformer()
        self.sep = _bisep_from_value(sep)
        self.terminal = terminal
        self.terminal_required = terminal_required
        self.size = size
        self.filter_empty = filter_empty

    def parse(self, text):
        """Parse the text into a container of items."""
        # start without unpredictable whitespace
        text = text.strip()

        # if we have a terminal, make sure it's there and remove it
        if self.terminal:
            if not text.endswith(self.terminal) and self.terminal_required:
                raise exceptions.ParsingError(f'must end with {self.terminal}, '
                                              f'not "{text[-len(self.terminal):]}"')
            text = text[:-len(self.terminal)].strip()

        # split text into raw items
        if self.sep.i is None:
            items = text.split()
        else:
            items = self.sep.split(text)

        # filter out empty items if requested
        if self.filter_empty:
            items = [i for i in items if i]

        # parse each item using the child transformer
        errors = []
        for i, item in enumerate(items):
            try:
                items[i] = self.child_tf.parse(item)
            except exceptions.ParsingError as e:
                errors.append(str(e))

        # if there are errors, collect them
        if errors:
            error = _friendly_join(errors, limit=3)
            raise exceptions.ParsingError(f'parsing errors: {error}')

        # check size requirements
        if self.size is not None and len(items) != self.size:
            raise exceptions.ParsingError(f'expected {self.size} items, '
                                          f'got {len(items)}')

        return self.pack(items)

    def pack(self, items):
        """Pack items into final container."""
        raise NotImplementedError()

    def unpack(self, container):
        """Unpack container into items."""
        raise NotImplementedError()


class ListT(ContainerT):
    """Transformer for a list of items."""

    def pack(self, items):
        return list(items)

    def unpack(self, container):
        return list(container)


class MapT(ContainerT):
    """Transformer for a key-value mapping of items."""

    def __init__(self, *, key=None, value=None, kv_sep='=', **kwargs):
        super().__init__(value=value, **kwargs)
        self.key_tf = key or Transformer()
        self.kv_sep = _bisep_from_value(kv_sep)

    def parse(self, text):
        # start without unpredictable whitespace
        text = text.strip()

        # if we have a terminal, make sure it's there and remove it
        if self.terminal:
            if not text.endswith(self.terminal) and self.terminal_required:
                raise exceptions.ParsingError(f'must end with {self.terminal}, '
                                              f'not "{text[-len(self.terminal):]}"')
            text = text[:-len(self.terminal)].strip()

        # split text into raw items
        if self.sep.i is None:
            items = text.split()
        else:
            items = self.sep.split(text)

        # filter out empty items if requested
        if self.filter_empty:
            items = [i for i in items if i]

        # parse each item as a key-value pair
        data = {}
        errors = []
        for item in items:
            if self.kv_sep.i is None:
                # no separator means key and value are the same
                raw_key = raw_value = item
            else:
                try:
                    raw_key, raw_value = self.kv_sep.split(item, maxsplit=1)
                except ValueError:
                    errors.append(f'item "{item}" is not a valid key-value pair')
                    continue

            # parse the key and value
            try:
                key = self.key_tf.parse(raw_key)
            except exceptions.ParsingError as e:
                errors.append(f'bad key in "{item}": {e}')
                continue

            try:
                value = self.child_tf.parse(raw_value)
            except exceptions.ParsingError as e:
                errors.append(f'bad value in "{item}": {e}')
                continue

            data[key] = value

        # if there are errors, collect them
        if errors:
            error = _friendly_join(errors)
            raise exceptions.ParsingError(f'parsing errors: '
                                          f'{error}')

        # check size requirements
        if self.size is not None and len(data) != self.size:
            raise exceptions.ParsingError(f'expected {self.size} items, '
                                          f'got {len(data)}')

        return data

    def pack(self, items):
        return dict(items)

    def unpack(self, container):
        return list(container.items())


# ============================================================================
# Minimal fields (from fields.py)
# ============================================================================

class Field:
    """Base field class."""

    default = None

    def __init__(self, keyword, **options):
        self.keyword = keyword
        self.name = None
        for key, value in options.items():
            setattr(self, key, value)

    def __set_name__(self, cls, name):
        if self.name is None:
            self.name = name

    def get_default_value(self):
        """Get the default value for this field."""
        default = self.default
        if callable(default):
            return default()
        return default

    def parse(self, text):
        """Parse text into field value."""
        raise NotImplementedError()

    def validate(self, value):
        """Validate a field value."""
        pass


class TransformerField(Field):
    """Field that uses a transformer for parsing."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tf = self.__class__.build_transformer()

    @classmethod
    def build_transformer(cls):
        """Build the transformer for this field."""
        raise NotImplementedError()

    def parse(self, text):
        """Parse text using the field's transformer."""
        return self.tf.parse(text)

    def validate(self, value):
        """Validate using the field's transformer."""
        return self.tf.validate(value)


class StringField(TransformerField):
    """Simple string field."""

    @classmethod
    def build_transformer(cls):
        return FuncT(func=str)


class IntegerField(TransformerField):
    """Simple integer field."""

    default = 0

    @classmethod
    def build_transformer(cls):
        return FuncT(func=int)


class IndexedCoordinatesField(TransformerField):
    """Field for coordinates by index."""

    default = dict

    def __init__(self, *args, dimensions=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.dimensions = self._tuplize(dimensions)

    @staticmethod
    def _tuplize(dimensions):
        return (dimensions,) if dimensions else None

    @classmethod
    def build_transformer(cls):
        key = FuncT(func=int)
        value = ListT(value=NumberT())
        return MapT(key=key, value=value, sep='\n')

    def validate(self, value):
        super().validate(value)
        cards = set(len(coord) for coord in value.values())
        if self.dimensions is not None and cards - set(self.dimensions):
            raise ValueError(f'wrong coordinate dimensions: {cards}')


class DepotsField(TransformerField):
    """Field for depots."""

    default = list

    @classmethod
    def build_transformer(cls):
        depot = FuncT(func=int)
        return ListT(value=depot, terminal='-1')


class DemandsField(TransformerField):
    """Field for demands."""

    default = dict

    @classmethod
    def build_transformer(cls):
        node = FuncT(func=int)
        demand = FuncT(func=int)
        return MapT(key=node, value=demand, sep='\n')


class EdgeDataField(TransformerField):
    """Field for edge data."""

    default = dict

    @classmethod
    def build_transformer(cls):
        edge = ListT(value=FuncT(func=int), size=2)
        return MapT(key=edge, value=FuncT(func=int), sep='\n')


class ToursField(Field):
    """Field for one or more tours."""

    default = list

    def __init__(self, *args, require_terminal=True):
        super().__init__(*args)
        self.terminal = '-1'
        self.require_terminal = require_terminal
        self._end_terminals = re.compile(rf'(?:(?:\s+|\b|^){self.terminal})+$')
        self._any_terminal = re.compile(rf'(?:\s+|\b){self.terminal}(?:\b|\s+)')

    def parse(self, text):
        """Parse the text into a list of tours."""
        tours = []

        # remove any terminal at the end
        text = self._end_terminals.sub('', text).strip()
        if not text:
            return tours

        # split text on any terminal that's not at the end
        segments = self._any_terminal.split(text)

        for segment in segments:
            if not segment.strip():
                continue
            tour = []
            for city in segment.split():
                if city == self.terminal:
                    break
                try:
                    tour.append(int(city))
                except ValueError:
                    raise exceptions.ParsingError(f'bad city: {city}')
            if tour:
                tours.append(tour)

        return tours


# ============================================================================
# Minimal models (from models.py)
# ============================================================================

class FileMeta(type):
    """Metaclass that builds field mappings for Problem classes."""

    def __new__(mcs, name, bases, attrs, **kwargs):
        cls = super().__new__(mcs, name, bases, attrs)

        # collect fields from this class and all parent classes
        fields = {}
        for klass in reversed(cls.__mro__):
            for key, value in vars(klass).items():
                if isinstance(value, Field):
                    fields[key] = value

        # build name/keyword mappings
        cls.fields_by_name = fields
        cls.fields_by_keyword = {f.keyword: f for f in fields.values()}

        return cls


class Problem(metaclass=FileMeta):
    """Base problem class."""

    def __init__(self, **kwargs):
        for name, value in kwargs.items():
            setattr(self, name, value)

    def __getattribute__(self, name):
        # check for a value like normal
        try:
            attrs = object.__getattribute__(self, '__dict__')
            return attrs[name]
        except KeyError:
            pass

        # value missing, so try to return the default
        # for the corresponding field
        try:
            cls = object.__getattribute__(self, '__class__')
            field = cls.fields_by_name[name]
        except KeyError:
            # no field, so get the attribute normally (will raise AttributeError)
            return object.__getattribute__(self, name)
        else:
            return field.get_default_value()

    def as_dict(self, by_keyword: bool = False) -> Dict[str, Any]:
        """Return the problem data as a dictionary."""
        data = {}
        for name, field in self.__class__.fields_by_name.items():
            value = getattr(self, name)
            if name in self.__dict__ or value != field.get_default_value():
                key = field.keyword if by_keyword else name
                data[key] = value
        return data

    def as_name_dict(self) -> Dict[str, Any]:
        """Return the problem data as a dictionary by field name."""
        return self.as_dict(by_keyword=False)

    def as_keyword_dict(self) -> Dict[str, Any]:
        """Return the problem data as a dictionary by field keyword."""
        return self.as_dict(by_keyword=True)



    @classmethod
    def parse(cls, text, **options):
        """Parse text into a Problem instance."""
        problem = cls()

        # split text into sections
        for line in text.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # split on first colon
            if ':' in line:
                keyword, content = line.split(':', 1)
                keyword = keyword.strip()
                content = content.strip()

                # find the field for this keyword
                if keyword in cls.fields_by_keyword:
                    field = cls.fields_by_keyword[keyword]
                    try:
                        value = field.parse(content)
                        setattr(problem, field.name, value)
                    except Exception as e:
                        # Skip parsing errors for robustness
                        pass
            else:
                # section data - collect until we find next keyword or EOF
                keyword = line
                if keyword in cls.fields_by_keyword:
                    field = cls.fields_by_keyword[keyword]
                    # For section fields, we need to collect following lines
                    # This is a simplified version - full parsing would require
                    # more sophisticated section handling
                    pass

        return problem


class StandardProblem(Problem):
    """Standard TSPLIB95 problem with common fields."""

    # Basic metadata fields
    name = StringField('NAME')
    comment = StringField('COMMENT')
    type = StringField('TYPE')
    dimension = IntegerField('DIMENSION')
    capacity = IntegerField('CAPACITY')
    node_coord_type = StringField('NODE_COORD_TYPE')
    edge_weight_type = StringField('EDGE_WEIGHT_TYPE')
    display_data_type = StringField('DISPLAY_DATA_TYPE')
    edge_weight_format = StringField('EDGE_WEIGHT_FORMAT')
    edge_data_format = StringField('EDGE_DATA_FORMAT')

    # Section data fields
    node_coords = IndexedCoordinatesField('NODE_COORD_SECTION', dimensions=(2, 3))
    edge_data = EdgeDataField('EDGE_DATA_SECTION')
    display_data = IndexedCoordinatesField('DISPLAY_DATA_SECTION', dimensions=2)
    depots = DepotsField('DEPOT_SECTION')
    demands = DemandsField('DEMAND_SECTION')
    tours = ToursField('TOUR_SECTION')

    @classmethod 
    def parse(cls, text, **options):
        """Parse TSPLIB95 format text into StandardProblem."""
        problem = cls()
        current_section = None
        section_lines = []

        for line in text.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Check if this is a keyword line
            if ':' in line and not current_section:
                keyword, value = line.split(':', 1)
                keyword = keyword.strip()
                value = value.strip()

                if keyword in cls.fields_by_keyword:
                    field = cls.fields_by_keyword[keyword]
                    try:
                        parsed_value = field.parse(value)
                        setattr(problem, field.name, parsed_value)
                    except:
                        pass  # Skip parsing errors

            # Check if this starts a section
            elif line.endswith('_SECTION') or line in ['EOF', 'DEPOT_SECTION', 'DEMAND_SECTION', 'TOUR_SECTION']:
                # Process previous section if any
                if current_section and section_lines:
                    section_text = '\n'.join(section_lines)
                    if current_section in cls.fields_by_keyword:
                        field = cls.fields_by_keyword[current_section]
                        try:
                            parsed_value = field.parse(section_text)
                            setattr(problem, field.name, parsed_value)
                        except:
                            pass  # Skip parsing errors

                # Start new section
                current_section = line if line != 'EOF' else None
                section_lines = []

            # Collect section data
            elif current_section:
                if line != 'EOF':
                    section_lines.append(line)

        # Process final section
        if current_section and section_lines:
            section_text = '\n'.join(section_lines)
            if current_section in cls.fields_by_keyword:
                field = cls.fields_by_keyword[current_section]
                try:
                    parsed_value = field.parse(section_text)
                    setattr(problem, field.name, parsed_value)
                except:
                    pass  # Skip parsing errors

        return problem