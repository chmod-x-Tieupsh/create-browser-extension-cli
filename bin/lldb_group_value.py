# Group value support for lldb, see CidrGroupValue.kt for details

import lldb
import re
import traceback

# _providers is a map from process id to ProcessGroupChildrenProviders holding
# group value children providers fro the process.
_providers = {}

# _group_value_type is a type we use to recognize group values.
# Group value is a children provider id casted to this type.
_group_value_type = 'void **********'

# _group_value_sbtype is a resolved _group_value_type.
_group_value_sbtype = None

def get_group_value_name(name):
    """
    Returns a name for a group value recognized by the IDE
    """

    return f'__jetbrains_group_value:{name}'


def create_group_value(valobj, encoded_group_name, group_children_provider):
    """
    Creates a group value with the given synthetic children provider.
    Use get_group_value_name() to create encoded_group_name.
    """

    process = valobj.process
    process_providers = _get_process_providers(process)
    if process_providers is None:
        return None
    provider_id = process_providers.add_provider(process, group_children_provider)
    # valobj.CreateValueFromExpression() triggers SyntheticChildrenProvider.update()
    # which potentially recomputes children (happens in Qt).
    # As a result children calculation becomes O(n^2), where n is number of children
    # and is too slow for larger containers.
    # valobj.synthetic_child_from_data doesn't trigger SyntheticChildrenProvider.update().
    group_type = resolve_group_value_type(process)
    data = lldb.SBData.CreateDataFromInt(provider_id, size=process.GetAddressByteSize())
    result = valobj.synthetic_child_from_data(encoded_group_name, data, group_type)
    return result


def resolve_group_value_type(process):
    global _group_value_sbtype
    if _group_value_sbtype is None:
        v = process.target.EvaluateExpression(f'({_group_value_type}) 0')
        _group_value_sbtype = v.type
    return _group_value_sbtype

class ProcessGroupChildrenProviders:
    """
    ProcessGroupChildrenProviders holds group value synthetic children providers for a process.

    Children providers don't depend on a process themselves, but we need to clean them when process
    is resumed. To achieve that we check the process StopID, this is why providers are bound to a process.
    """

    def __init__(self):
        self._stop_id = None
        self._providers = [] # list of group value children providers, a provider is identified by its position in this list

    def _clear_outdated_providers(self, process):
        current_stop_id = process.GetStopID()
        if self._stop_id is None or self._stop_id != current_stop_id:
            self._providers.clear()
            self._stop_id = current_stop_id

    def add_provider(self, process, provider):
        self._clear_outdated_providers(process)
        provider_id = len(self._providers)
        self._providers.append(provider)
        return provider_id

    def get_provider(self, provider_id):
        if provider_id < len(self._providers):
            return self._providers[provider_id]
        else:
            print(f'Group value provider_id is out of bounds: provider_id={provider_id}, upper_bound={len(self._providers)}')
            return None


def _get_process_providers(process):
    if not process.IsValid():
        return None
    process_id = process.GetUniqueID()
    result = _providers.get(process_id, None)
    if result is None:
        result = ProcessGroupChildrenProviders()
        _providers[process_id] = result
    return result


class GroupValueChildrenProvider:
    """
    GroupValueChildrenProvider provides children for group values.

    Group values are pointers of the type _group_value_type which is
    hopefully rarely used in real program. A value of the pointer is
    the id of the provider which should be used to compute children.

    This provider is called for every group value and acts as a dispatcher.
    It retrieves a provider_id from the pointer, finds the real children
    provider, and dispatches all methods to the found provider.
    """

    def __init__(self, valobj, internal_dict):
        self._valobj = valobj
        self._provider = None

    def num_children(self, max_children):
        if self._provider is not None:
            return self._provider.num_children(max_children)
        return 0

    def get_child_index(self, name):
        if self._provider is not None:
            return self._provider.get_child_index(name)
        return -1

    def get_child_at_index(self, index):
        if self._provider is not None:
            return self._provider.get_child_at_index(index)
        return None

    def has_children(self):
        if self._provider is not None and hasattr(self._provider, 'has_children'): # has_children() is optional
            return self._provider.has_children()
        return True

    def get_value(self):
        if self._provider is not None and hasattr(self._provider, 'get_value'): # get_value() is optional
            return self._provider.get_value()
        return None

    def update(self):
        try:
            process_providers = _get_process_providers(self._valobj.process)
            if process_providers is None:
                return
            provider_id = self._valobj.unsigned
            self._provider = process_providers.get_provider(provider_id)
            if hasattr(self._provider, 'update'): # update() is optional
                return self._provider.update()
        except:
            traceback.print_exc()
        return False



def init_group_value_support(debugger):
    debugger.HandleCommand(f'type synthetic add -l lldb_formatters.lldb_group_value.GroupValueChildrenProvider -x "^{re.escape(_group_value_type)}$"')
