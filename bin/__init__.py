import lldb.formatters.cpp.gnu_libstdcpp
import lldb_formatters.jetbrains_stl_formatters
from lldb_formatters.lldb_group_value import init_group_value_support

def __lldb_init_module(debugger, dict):
    debugger.HandleCommand('type synthetic add -l lldb_formatters.jetbrains_stl_formatters.StdDequeSynthProvider -x "^std::deque<.+> >(( )?&)?$"')
    debugger.HandleCommand('type summary add -F lldb_formatters.jetbrains_stl_formatters.SizeSummaryProvider -e -x "^std::deque<.+> >(( )?&)?$"')

    debugger.HandleCommand('type synthetic add -l lldb_formatters.jetbrains_stl_formatters.StdHashtableSynthProvider -x "^(std::tr1::)unordered_set<.+>.*"')
    debugger.HandleCommand('type summary add -F lldb_formatters.jetbrains_stl_formatters.SizeSummaryProvider -e -x "^(std::tr1::)unordered_set<.+>.*"')

    debugger.HandleCommand('type synthetic add -l lldb_formatters.jetbrains_stl_formatters.StdHashtableSynthProvider -x "^(std::tr1::)unordered_map<.+>.*"')
    debugger.HandleCommand('type summary add -F lldb_formatters.jetbrains_stl_formatters.SizeSummaryProvider -e -x "^(std::tr1::)unordered_map<.+>.*"')

    debugger.HandleCommand('type synthetic add -l lldb.formatters.cpp.gnu_libstdcpp.StdMapLikeSynthProvider -x "^std::multimap<.+> >(( )?&)?$"')
    debugger.HandleCommand('type summary add -F lldb_formatters.jetbrains_stl_formatters.SizeSummaryProvider -e -x "^std::multimap<.+> >(( )?&)?$"')

    debugger.HandleCommand('type synthetic add -l lldb_formatters.jetbrains_stl_formatters.StdSetSynthProvider -x "^std::set<.+> >(( )?&)?$"')
    debugger.HandleCommand('type summary add -F lldb_formatters.jetbrains_stl_formatters.SizeSummaryProvider -e -x "^std::set<.+> >(( )?&)?$"')

    debugger.HandleCommand('type synthetic add -l lldb_formatters.jetbrains_stl_formatters.StdSetSynthProvider -x "^std::multiset<.+> >(( )?&)?$"')
    debugger.HandleCommand('type summary add -F lldb_formatters.jetbrains_stl_formatters.SizeSummaryProvider -e -x "^std::multiset<.+> >(( )?&)?$"')

    init_group_value_support(debugger)
