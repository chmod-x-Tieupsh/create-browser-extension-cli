from dumper import ReportItem, TopLevelItem
from lldbbridge import Dumper, SummaryDumper, SummaryProvider, SyntheticChildrenProvider
from lldb_formatters.lldb_group_value import get_group_value_name, create_group_value
import traceback

class CidrQNode:
    def __init__(self, parent_node, is_group_node):
        self.parent_node = parent_node
        self.is_group_node = is_group_node
        self.name = None
        self.value = None
        self.report_item = None # dumper.ReportItem
        self.children = []
        self.key = None
        self.key_encoding = None
        self.key_prefix = ''

    def set_name(self, name):
        if name is None:
            return

        if isinstance(name, int):
            self.name = f'[{name}]'
        else:
            self.name = str(name)

    def get_name(self):
        name = self.name if self.name is not None else ''
        if not self.is_group_node:
            return name
        if self.key is not None:
            name = f'{self.key_prefix}{decode_value(self.key, self.key_encoding)}'
            if self.report_item is not None and self.report_item.value is not None:
                name += ' = '
                name += decode_value(self.report_item.value, self.report_item.encoding)

        return get_group_value_name(name)

    def __repr__(self):
        return (
            f"CidrQNode(name={self.name}, value={self.value}, "
            f"is_group_node={self.is_group_node}, key={self.key}, "
            f"key_encoding={self.key_encoding}, key_prefix={self.key_prefix})"
        )


text_encodings = {'utf16', 'utf8', 'latin1'}
special_encodings = {'empty', 'undefined', 'null', 'notaccessible', 'optimizedout', 'nullreference', 'emptystructure', 'uninitialized', 'invalid', 'notcallable', 'outofscope'}

def decode_value(v, encoding=None):
    debugLog(f'decode_value({v}, {encoding})')
    if not isinstance(encoding, str):
        return str(v)
    if encoding == 'itemcount':
        return f'<{v} items>'
    if encoding == 'minimumitemcount':
        return f'<at least {v} items>'
    if encoding in text_encodings:
        try:
            decodedValue = Dumper.hexdecode(v, encoding)
            return f'"{decodedValue}"'
        except:
            pass
    if encoding in special_encodings:
        return f'<{encoding}>'
    return f'<{v}, encoding={encoding}>'


def get_summary(valobj, internal_dict, options=None):
    """
    Get_summary provides summary for Qt classes.

    It is the same as lldbbridge.SummaryProvider.provide_summary, but without
    fallback to empty summary if 'qt' is not found in internal_dict and with
    additional error handling (get_summary fails in case of unsupported encoding).
    """

    with SummaryDumper.shared(valobj) as dumper:
        if not isDumperEnabled(dumper):
            return ''

        parent = getCidrNode(dumper)
        provider = SummaryProvider(valobj)
        setCidrNode(dumper, CidrQNode(parent, False))
        try:
            provider.update()
            return provider.get_summary(options)
        except:
            debugLog('SummaryProvider.get_summary failed')
            value = provider.summary.get('value', None)
            encoding = provider.summary.get('valueencoded', None)
            return decode_value(value, encoding)
        finally:
            setCidrNode(dumper, parent)


class CidrSyntheticChildrenProvider(SyntheticChildrenProvider):
    def __init__(self, valobj, dict):
        SyntheticChildrenProvider.__init__(self, valobj, dict)

    def update(self):
        with SummaryDumper.shared(self.valobj) as dumper:
            if not isDumperEnabled(dumper):
                return False

            parent = getCidrNode(dumper)
            try:
                setCidrNode(dumper, CidrQNode(parent, False))
                setGroupNode(self, False)
                super().update()
            finally:
                setCidrNode(dumper, parent)

        return False

    def create_value(self, child, name=''):
        debugLog(f'create_value(child={child}, name={name})')
        cidrNode = child.get('cidrNode', None)

        value = None
        if cidrNode and cidrNode.is_group_node:
            child_dicts = [{'name': o.name, 'cidrNode': o} for o in cidrNode.children]
            name = cidrNode.get_name()
            return create_group_value(self.valobj, name, CidrQtGroupValueChildrenProvider(self, child_dicts))

        if cidrNode and cidrNode.value:
            value = cidrNode.value
            if value.laddress is not None and value.type is not None and value.type.name is not None:
                child_type = value.type.name
                value_type = None
                with SummaryDumper.shared(self.valobj) as dumper:
                    value_type = dumper.lookupNativeType(child_type)
                if not value_type or not value_type.IsValid():
                    debugLog('value_type is not found or invalid')
                    return None
                value = self.valobj.synthetic_child_from_address(name, value.laddress, SummaryProvider.VOID_PTR_TYPE).Cast(value_type)
                return value

        debugLog(f'create_value returns None')
        return None

class CidrQtGroupValueChildrenProvider:
    def __init__(self, outer_instance, children):
        self.outer_instance = outer_instance
        self._children = children

    def num_children(self, max_children):
        return len(self._children)

    def get_child_index(self, name):
        for i, child in enumerate(self._children):
            child_name = child.get('name', "[%s]" % i)
            if child_name == name:
                return i
        return -1

    def get_child_at_index(self, index):
        if index < len(self._children):
            child = self._children[index]
            name = child.get('name', "[%s]" % index)
            value = self.outer_instance.create_value(child, name)
            return value
        return None

    def has_children(self):
        return len(self._children) > 0

    def get_value(self):
        return None

def getCidrNode(dumper):
    return getattr(dumper, '__cidr_node', None)

def setCidrNode(dumper, node):
    setattr(dumper, '__cidr_node', node)

def isGroupNode(dumper):
    return getattr(dumper, '__is_group_node', False)

def setGroupNode(dumper, isGroupNode):
    setattr(dumper, '__is_group_node', isGroupNode)

def isDumperEnabled(dumper):
    return getattr(dumper, '__is_dumper_enabled', True)

def setDumperEnabled(dumper, isEnabled):
    setattr(dumper, '__is_dumper_enabled', isEnabled)

def incIndent(dumper):
    indent = getIndent(dumper)
    setIndent(dumper, indent + 1)

def decIndent(dumper):
    indent = getIndent(dumper)
    if indent > 0:
        setIndent(dumper, indent - 1)

def getIndent(dumper):
    return getattr(dumper, '__cidr_indent', 0)

def setIndent(dumper, indent):
    setattr(dumper, '__cidr_indent', indent)

def SummaryDumper_dump_summary(self, valobj, expanded=False):
    # self is a lldbbridge.SummaryDumper
    #
    # SummaryDumper.dump_summary uses pygdbmi library to parse output
    # produced by dumpers.
    # To avoid bundling pygdbmi we return the same result without using it.
    # SummaryDumper.dump_summary returns a dictionary which is used
    # by SummaryProvider.get_summary() producing a value summary,
    # and by SyntheticChildrenProvider.update() in order to compute children.

    try:
        value = self.fromNativeValue(valobj)

        # Expand variable if we need synthetic children
        oldExpanded = self.expandedINames
        self.expandedINames = {'__cidr_printer__': 100} if expanded else {}
        currentValue = None
        currentCidrNode = None
        with TopLevelItem(self, '__cidr_printer__'):
            self.putItem(value)
            currentValue = self.currentValue
            currentCidrNode = getCidrNode(self) # capture node before it is erased in exitSubItem

        result = {'valueencoded': currentValue.encoding, 'value': currentValue.value} # these keys are used by SummaryProvider.get_summary()
        children = []
        for child in currentCidrNode.children:
            child_dict = {'cidrNode': child}
            # SyntheticChildrenProvider.get_child_at_index does
            # name = child.get('name', "[%s]" % index)
            # which returns None if we assign None as a value for the 'name' key
            # To make fallback to '[index]' name work we put only non None names:
            if child.name:
                child_dict['name'] = child.name
            children.append(child_dict)
        result['children'] = children # children are used by SyntheticChildrenProvider.update()

        return result
    except:
        print("Failed to dump summary")
        print(traceback.format_exc())
        return None

def SummaryDumper_patchEnterSubItem(original):
    def enterSubItem(self, item):
        dumperLog(self, f'enterSubItem({item})')

        parent = getCidrNode(self)
        setCidrNode(self, CidrQNode(parent, isGroupNode(self)))
        setGroupNode(self, False)

        incIndent(self)

        original(self, item)

    return enterSubItem

def SummaryDumper_patchExitSubItem(original):
    def exitSubItem(self, item, exType, exValue, exTraceBack):
        child = getCidrNode(self)
        child.report_item = self.currentValue

        original(self, item, exType, exValue, exTraceBack)

        child = getCidrNode(self)
        parent = child.parent_node
        if parent is not None:
            parent.children.append(child)
        setCidrNode(self, parent)

        decIndent(self)
        dumperLog(self, 'exitSubItem')

    return exitSubItem

def SummaryDumper_patchPutItem(original):
    def putItem(self, value):
        dumperLog(self, f'putItem({value})')

        node = getCidrNode(self)
        node.value = value
        original(self, value)

    return putItem

def SummaryDumper_patchPutValue(original):
    def putValue(self, value, encoding=None, priority=0, length=None):
        # override for logging only
        dumperLog(self, f'putValue(value={value}, encoding={encoding}, priority={priority}, length={length})')
        original(self, value, encoding, priority, length)
    return putValue

def SummaryDumper_patchPutPairItem(original):
    def putPairItem(self, index, pair, keyName='first', valueName='second'):
        dumperLog(self, f'putPairItem')
        setGroupNode(self, True)
        original(self, index, pair, keyName, valueName)

    return putPairItem

def SummaryDumper_patchPutField(original):
    def putField(self, name, value):
        dumperLog(self, f'putField({name}, {value})')

        if name == 'name':
            getCidrNode(self).set_name(value)

        # see putPairContents() for key-related handling
        if name == 'key':
            getCidrNode(self).key = value
        elif name == 'keyencoded':
            getCidrNode(self).key_encoding = value
        elif name == 'keyprefix':
            getCidrNode(self).key_prefix = value

        original(self, name, value)
    return putField

def SummaryDumper_childRange(self):
    result = range(self.currentNumChild)
    dumperLog(self, f'childRange() = {result}')
    return result

def SummaryDumper_fromNativeValue(original):
    def fromNativeValue(self, nativeValue):
        enabled = isDumperEnabled(self)
        setDumperEnabled(self, False)
        try:
            return original(self, nativeValue)
        finally:
            setDumperEnabled(self, enabled)
    return fromNativeValue

def dumperLog(dumper, msg):
    debugLog(msg, indent = getIndent(dumper))

log_enabled = False

def debugLog(msg, indent = 0):
    indentStr = "  " * indent
    if log_enabled:
        print(f'{indentStr}{msg}')

def patch_summary_dumper(dumper):
    # by default dumpermodules is ['qttypes'],
    # 'stdtypes' and 'libcpp_stdtypes' are needed to make QMap work which is based on std::map
    reloadDumpers = False
    for module in ['stdtypes', 'libcpp_stdtypes']:
        if module not in dumper.dumpermodules:
            dumper.dumpermodules.append(module)
            reloadDumpers = True
    if reloadDumpers:
        dumper.loadDumpers({})

    # lldbbridge uses a shared dumber instance via static methods.
    # This prevents us from simply extending the dumper.
    # To change dumper logic we patch its methods and augment them
    # with additional data collection which is mostly needed to produce
    # proper synthetic children (lldbbridge.SyntheticChildrenProvider doesn't
    # support map entries).
    SummaryDumper.dump_summary = SummaryDumper_dump_summary
    SummaryDumper.enterSubItem = SummaryDumper_patchEnterSubItem(SummaryDumper.enterSubItem)
    SummaryDumper.exitSubItem = SummaryDumper_patchExitSubItem(SummaryDumper.exitSubItem)
    SummaryDumper.putItem = SummaryDumper_patchPutItem(SummaryDumper.putItem)
    SummaryDumper.putValue = SummaryDumper_patchPutValue(SummaryDumper.putValue)
    SummaryDumper.putPairItem = SummaryDumper_patchPutPairItem(SummaryDumper.putPairItem)
    SummaryDumper.putField = SummaryDumper_patchPutField(SummaryDumper.putField)
    SummaryDumper.childRange = SummaryDumper_childRange
    SummaryDumper.fromNativeValue = SummaryDumper_fromNativeValue(SummaryDumper.fromNativeValue)
