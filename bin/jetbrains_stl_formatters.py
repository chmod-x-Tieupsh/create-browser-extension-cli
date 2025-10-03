from __future__ import (absolute_import, division, print_function)
import lldb


def extract_template_arg(valobj, i):
    deque_type = valobj.GetType().GetUnqualifiedType()
    if deque_type.IsReferenceType():
        deque_type = deque_type.GetDereferencedType()
    if deque_type.GetNumberOfTemplateArguments() > i:
        data_type = deque_type.GetTemplateArgumentType(i)
    else:
        data_type = None
    return data_type


def size_as_summary(valobj):
    return 'size=' + str(valobj.GetNumChildren())

class StdDequeSynthProvider:

    def __init__(self, valobj, dict):
        self.valobj = valobj
        self.garbage = False

    def num_children(self):
        if self.garbage:
            return 0
        finish_node = self.finish.GetChildMemberWithName("_M_node")
        start_node = self.start.GetChildMemberWithName("_M_node")

        finish_cur = self.finish.GetChildMemberWithName("_M_cur")
        finish_first = self.finish.GetChildMemberWithName("_M_first")
        return (finish_node.GetValueAsUnsigned() - start_node.GetValueAsUnsigned()) // self.pointer_type.GetByteSize() + \
               (finish_cur.GetValueAsUnsigned() - finish_first.GetValueAsUnsigned()) // self.data_size

    def get_child_index(self,name):
        try:
            return int(name.lstrip('[').rstrip(']'))
        except:
            return -1

    def get_child_at_index(self,index):
        if self.garbage:
            return None
        my_buffer_size = self.buffer_size()

        node_index = index // my_buffer_size
        index_in_node = index % my_buffer_size

        first_node = self.start.GetChildMemberWithName("_M_node")
        first_node_address = first_node.GetValueAsUnsigned()

        my_node_address = node_index * self.pointer_type.GetByteSize() + first_node_address

        first_element_in_node = first_node.CreateValueFromAddress("", my_node_address, self.pointer_type)

        return first_element_in_node.CreateChildAtOffset('['+str(index)+']', index_in_node * self.data_size, self.data_type)

    def check_iterator(self, iterator):
        if self.garbage:
            pass

        cur = iterator.GetChildMemberWithName("_M_cur").GetValueAsUnsigned()
        first = iterator.GetChildMemberWithName("_M_first").GetValueAsUnsigned()
        last = iterator.GetChildMemberWithName("_M_last").GetValueAsUnsigned()
        node = iterator.GetChildMemberWithName("_M_node").GetValueAsUnsigned()

        if not(first <= cur <= last and node != 0):
            self.garbage = True

    def update(self):
        self.data_type = extract_template_arg(self.valobj, 0)
        self.pointer_type = self.data_type.GetPointerType()
        self.data_size = self.data_type.GetByteSize()

        self.impl = self.valobj.GetChildMemberWithName("_M_impl")

        self.start = self.impl.GetChildMemberWithName("_M_start")
        self.finish = self.impl.GetChildMemberWithName("_M_finish")



        self.check_iterator(self.start)
        self.check_iterator(self.finish)
        pass

    def buffer_size(self):
        element_size = self.data_type.GetByteSize()
        return 512 // element_size if element_size < 512 else 1

def SizeSummaryProvider(valobj,dict):
    return size_as_summary(valobj)


class StdDeque11SynthProvider:

    def __init__(self, valobj, dict):
        self.valobj = valobj

    def num_children(self):
#        if self.garbage:
#            return 0
        return self.valobj.GetChildMemberWithName("__size_").GetChildMemberWithName("__first_").GetValueAsUnsigned()


    def get_child_index(self,name):
        try:
            return int(name.lstrip('[').rstrip(']'))
        except:
            return -1

    def get_child_at_index(self,index):
#        if self.garbage:
#            return None
        my_buffer_size = self.buffer_size()

        node_index = index // my_buffer_size
        index_in_node = index % my_buffer_size

        first_node = self.map_begin

        first_node_address = first_node.GetValueAsUnsigned()
        my_node_address = node_index * self.pointer_type.GetByteSize() + first_node_address

        first_element_in_node = first_node.CreateValueFromAddress("", my_node_address, self.pointer_type)
        return first_element_in_node.CreateChildAtOffset('['+str(index)+']', index_in_node * self.data_size, self.data_type)

    def update(self):
        self.data_type = extract_template_arg(self.valobj, 0)
        self.pointer_type = self.data_type.GetPointerType()
        self.data_size = self.data_type.GetByteSize()

        self.map = self.valobj.GetChildMemberWithName("__map_")

        self.map_begin = self.map.GetChildMemberWithName("__begin_")
#        self.map_end = map.GetChildMemberWithName("__end_")
#        self.map_first = map.GetChildMemberWithName("__first_")

#        if self.map_begin.GetValueAsUnsigned() > self.map_end.GetValueAsUnsigned() or self.map_first.GetValueAsUnsigned() != self.map_begin.GetValueAsUnsigned():
#            self.garbage = True

        pass

    def buffer_size(self):
        # deque
        # static const difference_type __block_size = sizeof(value_type) < 256 ? 4096 // sizeof(value_type) : 16;
        return 4096 // self.data_size if self.data_size < 256 else 16

class StdSetSynthProvider:

    def __init__(self, valobj, dict):
        logger = lldb.formatters.Logger.Logger()
        self.valobj = valobj;
        self.count = None
        logger >> "Providing synthetic children for a map named " + str(valobj.GetName())

    def update(self):
        logger = lldb.formatters.Logger.Logger()
        # preemptively setting this to None - we might end up changing our mind later
        self.count = None
        try:
            # we will set this to True if we find out that discovering a node in the map takes more steps than the overall size of the RB tree
            # if this gets set to True, then we will merrily return None for any child from that moment on
            self.garbage = False
            self.Mt = self.valobj.GetChildMemberWithName('_M_t')
            self.Mimpl = self.Mt.GetChildMemberWithName('_M_impl')
            self.Mheader = self.Mimpl.GetChildMemberWithName('_M_header')

            self.data_type = extract_template_arg(self.valobj, 0)

            self.Mroot = self.Mheader.GetChildMemberWithName('_M_parent')
            self.data_size = self.data_type.GetByteSize()
            self.skip_size = self.Mheader.GetType().GetByteSize()
        except:
            pass

    def num_children(self):
        if self.count == None:
            self.count = self.num_children_impl()
        return self.count

    def num_children_impl(self):
        logger = lldb.formatters.Logger.Logger()
        try:
            root_ptr_val = self.node_ptr_value(self.Mroot)
            if root_ptr_val == 0:
                return 0;
            count = self.Mimpl.GetChildMemberWithName('_M_node_count').GetValueAsUnsigned(0)
            logger >> "I have " + str(count) + " children available"
            return count
        except:
            return 0;

    def get_child_index(self,name):
        logger = lldb.formatters.Logger.Logger()
        try:
            return int(name.lstrip('[').rstrip(']'))
        except:
            return -1

    def get_child_at_index(self,index):
        logger = lldb.formatters.Logger.Logger()
        logger >> "Being asked to fetch child[" + str(index) + "]"
        if index < 0:
            return None
        if index >= self.num_children():
            return None;
        if self.garbage:
            logger >> "Returning None since we are a garbage tree"
            return None
        try:
            offset = index
            current = self.left(self.Mheader);
            while offset > 0:
                current = self.increment_node(current)
                offset = offset - 1;
            # skip all the base stuff and get at the data
            return current.CreateChildAtOffset('['+str(index)+']',self.skip_size,self.data_type)
        except:
            return None

    # utility functions
    def node_ptr_value(self,node):
        logger = lldb.formatters.Logger.Logger()
        return node.GetValueAsUnsigned(0)

    def right(self,node):
        logger = lldb.formatters.Logger.Logger()
        return node.GetChildMemberWithName("_M_right");

    def left(self,node):
        logger = lldb.formatters.Logger.Logger()
        return node.GetChildMemberWithName("_M_left");

    def parent(self,node):
        logger = lldb.formatters.Logger.Logger()
        return node.GetChildMemberWithName("_M_parent");

    # from libstdc++ implementation of iterator for rbtree
    def increment_node(self,node):
        logger = lldb.formatters.Logger.Logger()
        max_steps = self.num_children()
        if self.node_ptr_value(self.right(node)) != 0:
            x = self.right(node);
            max_steps -= 1
            while self.node_ptr_value(self.left(x)) != 0:
                x = self.left(x);
                max_steps -= 1
                logger >> str(max_steps) + " more to go before giving up"
                if max_steps <= 0:
                    self.garbage = True
                    return None
            return x;
        else:
            x = node;
            y = self.parent(x)
            max_steps -= 1
            while(self.node_ptr_value(x) == self.node_ptr_value(self.right(y))):
                x = y;
                y = self.parent(y);
                max_steps -= 1
                logger >> str(max_steps) + " more to go before giving up"
                if max_steps <= 0:
                    self.garbage = True
                    return None
            if self.node_ptr_value(self.right(x)) != self.node_ptr_value(y):
                x = y;
            return x;


class StdHashtableSynthProvider:

    def __init__(self, valobj, dict):
        self.valobj = valobj

    def num_children(self):
        return self.children_count

    def get_child_index(self,name):
        try:
            return int(name.lstrip('[').rstrip(']'))
        except:
            return -1

    def get_child_at_index(self,index):
        if self.i > index:
            return None

        while self.i < self.children_count and self.bucket_index < self.bucket_count:
            bucket_ptr = self.buckets_ptr.GetValueAsUnsigned() + self.buckets_ptr.GetByteSize() * self.bucket_index
            hash_node_ptr = self.buckets_ptr.CreateValueFromAddress("", bucket_ptr, self.buckets_ptr.GetType().GetPointeeType())

            local_i = self.i
            while hash_node_ptr.GetValueAsUnsigned():
                hash_node = hash_node_ptr.Dereference()
                if local_i == index:
                    value = hash_node.GetChildMemberWithName("_M_v")
                    return value.CreateChildAtOffset("[" + str(local_i) + "]", 0, value.GetType())
                hash_node_ptr = hash_node.GetChildMemberWithName("_M_next")
                local_i += 1
            self.i = local_i
            self.bucket_index += 1
        return None


    def update(self):
        self.children_count = self.valobj.GetChildMemberWithName("_M_element_count").GetValueAsUnsigned()
        self.buckets_ptr = self.valobj.GetChildMemberWithName("_M_buckets")
        self.bucket_count = self.valobj.GetChildMemberWithName("_M_bucket_count").GetValueAsUnsigned()

        self.i = 0
        self.bucket_index = 0
        pass


# a tree node - this class makes the syntax in the actual iterator nicer
# to read and maintain


class stdmap_iterator_node:

    def _left_impl(self):
        logger = lldb.formatters.Logger.Logger()
        return stdmap_iterator_node(
            self.node.GetChildMemberWithName("__left_"),
            self.node_type)

    def _right_impl(self):
        logger = lldb.formatters.Logger.Logger()
        return stdmap_iterator_node(
            self.node.GetChildMemberWithName("__right_"),
            self.node_type)

    def _parent_impl(self):
        logger = lldb.formatters.Logger.Logger()
        return stdmap_iterator_node(
            self.node.GetChildMemberWithName("__parent_"),
            self.node_type)

    def _value_impl(self):
        logger = lldb.formatters.Logger.Logger()
        return self.node.GetValueAsUnsigned(0)

    def _sbvalue_impl(self):
        logger = lldb.formatters.Logger.Logger()
        return self.node

    def _null_impl(self):
        logger = lldb.formatters.Logger.Logger()
        return self.value == 0

    def __init__(self, node, node_type=None):
        logger = lldb.formatters.Logger.Logger()
        if node_type is None:
            node_type = node.GetType()
            self.node = node
        else:
            self.node = node.Cast(node_type)
        self.node_type = node_type

    left = property(_left_impl, None)
    right = property(_right_impl, None)
    parent = property(_parent_impl, None)
    value = property(_value_impl, None)
    is_null = property(_null_impl, None)
    sbvalue = property(_sbvalue_impl, None)

# a Python implementation of the tree iterator used by libc++


class stdmap_iterator:

    def tree_min(self, x):
        logger = lldb.formatters.Logger.Logger()
        steps = 0
        if x.is_null:
            return None
        while (not x.left.is_null):
            x = x.left
            steps += 1
            if steps > self.max_count:
                logger >> "Returning None - we overflowed"
                return None
        return x

    def tree_max(self, x):
        logger = lldb.formatters.Logger.Logger()
        if x.is_null:
            return None
        while (not x.right.is_null):
            x = x.right
        return x

    def tree_is_left_child(self, x):
        logger = lldb.formatters.Logger.Logger()
        if x.is_null:
            return None
        return True if x.value == x.parent.left.value else False

    def increment_node(self, node):
        logger = lldb.formatters.Logger.Logger()
        if node.is_null:
            return None
        if not node.right.is_null:
            return self.tree_min(node.right)
        steps = 0
        while (not self.tree_is_left_child(node)):
            steps += 1
            if steps > self.max_count:
                logger >> "Returning None - we overflowed"
                return None
            node = node.parent
        return node.parent

    def __init__(self, node, max_count=0):
        logger = lldb.formatters.Logger.Logger()
        # we convert the SBValue to an internal node object on entry
        self.node = stdmap_iterator_node(node)
        self.max_count = max_count

    def value(self):
        logger = lldb.formatters.Logger.Logger()
        return self.node.sbvalue  # and return the SBValue back on exit

    def next(self):
        logger = lldb.formatters.Logger.Logger()
        node = self.increment_node(self.node)
        if node is not None and node.sbvalue.IsValid() and not(node.is_null):
            self.node = node
            return self.value()
        else:
            return None

    def advance(self, N):
        logger = lldb.formatters.Logger.Logger()
        if N < 0:
            return None
        if N == 0:
            return self.value()
        if N == 1:
            return self.next()
        while N > 0:
            if self.next() is None:
                return None
            N = N - 1
        return self.value()


class stdmap_SynthProvider:

    def __init__(self, valobj, dict):
        logger = lldb.formatters.Logger.Logger()
        self.valobj = valobj
        self.pointer_size = self.valobj.GetProcess().GetAddressByteSize()
        self.count = None

    def update(self):
        logger = lldb.formatters.Logger.Logger()
        self.count = None
        try:
            # we will set this to True if we find out that discovering a node in the map takes more steps than the overall size of the RB tree
            # if this gets set to True, then we will merrily return None for
            # any child from that moment on
            self.garbage = False
            self.tree = self.valobj.GetChildMemberWithName('__tree_')
            self.root_node = self._cast_root_node(self.tree, self.tree.GetChildMemberWithName('__begin_node_'))

            # this data is either lazily-calculated, or cannot be inferred at this moment
            # we still need to mark it as None, meaning "please set me ASAP"
            self.data_type = None
            self.data_size = None
            self.skip_size = None

            self.elements_cache = []
            self.iterator = stdmap_iterator(self.root_node, max_count=self.num_children())
        except:
            pass

    def _cast_root_node(tree, node):
        i = 0
        while True:
            member_function = tree.GetType().GetMemberFunctionAtIndex(i)
            if not member_function.IsValid():
                break
            if member_function.GetName() == '__root':
                return node.Cast(member_function.GetReturnType())
                break
            i += 1

        return node

    def num_children(self):
        if self.count is None:
            self.count = self.num_children_impl()
        return self.count

    def num_children_impl(self):
        logger = lldb.formatters.Logger.Logger()
        try:
            return self.valobj.GetChildMemberWithName('__tree_').GetChildMemberWithName(
                '__pair3_').GetChildMemberWithName('__first_').GetValueAsUnsigned()
        except:
            return 0

    def has_children(self):
        return True

    def get_data_type(self):
        logger = lldb.formatters.Logger.Logger()
        if self.data_type is None or self.data_size is None:
            if self.num_children() == 0:
                return False
            deref = self.root_node.Dereference()
            if not(deref.IsValid()):
                return False
            value = deref.GetChildMemberWithName('__value_')
            if not(value.IsValid()):
                return False
            value = value.GetChildMemberWithName('__cc') or value
            self.data_type = value.GetType()
            self.data_size = self.data_type.GetByteSize()
            self.skip_size = None
            return True
        else:
            return True

    def get_value_offset(self, node):
        logger = lldb.formatters.Logger.Logger()
        if self.skip_size is None:
            node_type = node.GetType()
            fields_count = node_type.GetNumberOfFields()
            for i in range(fields_count):
                field = node_type.GetFieldAtIndex(i)
                if field.GetName() == '__value_':
                    self.skip_size = field.GetOffsetInBytes()
                    break
        return (self.skip_size is not None)

    def get_child_index(self, name):
        logger = lldb.formatters.Logger.Logger()
        try:
            return int(name.lstrip('[').rstrip(']'))
        except:
            return -1

    def get_child_at_index(self, index):
        logger = lldb.formatters.Logger.Logger()
        logger >> "Retrieving child " + str(index)
        if index < 0:
            return None
        if index >= self.num_children():
            return None
        if self.garbage:
            logger >> "Returning None since this tree is garbage"
            return None
        try:
            logger >> " : cache size starts with %d elements" % len(
                self.elements_cache)
            while index >= len(self.elements_cache):
                # XXX the following comment is a blatant lie. -- Eldar
                #
                # the debug info for libc++ std::map is such that __begin_node_ has a very nice and useful type
                # out of which we can grab the information we need - every other node has a less informative
                # type which omits all value information and only contains housekeeping information for the RB tree
                # hence, we need to know if we are at a node != 0, so that we can
                # still get at the data
                need_to_skip = (index > 0)
                current = self.iterator.advance(int(need_to_skip))
                if current is None:
                    logger >> "Tree is garbage - returning None"
                    self.garbage = True
                    return None
                if self.get_data_type():
                    if not(need_to_skip):
                        current = current.Dereference()
                        obj = current.GetChildMemberWithName('__value_')
                        obj_data = obj.GetData()
                        # make sure we have a valid offset for the next items
                        self.get_value_offset(current)
                        # we do not return __value_ because then we would end up with a child named
                        # __value_ instead of [0]
                        self.elements_cache.append(self.valobj.CreateValueFromData(
                            '[' + str(index) + ']', obj_data, self.data_type))
                    else:
                        # FIXME we need to have accessed item 0 before accessing
                        # any other item!
                        if self.skip_size is None:
                            logger >> "You asked for item > 0 before asking for item == 0, I will fetch 0 now then retry"
                            if self.get_child_at_index(0):
                                return self.get_child_at_index(index)
                            else:
                                logger >> "item == 0 could not be found. sorry, nothing can be done here."
                                return None
                        self.elements_cache.append(current.CreateChildAtOffset(
                            '[' + str(index) + ']', self.skip_size, self.data_type))
                else:
                    logger >> "Unable to infer data-type - returning None (should mark tree as garbage here?)"
                    self.garbage = True
                    return None
            else:
                logger >> " : cache size ends with %d elements" % len(self.elements_cache)
                value = self.elements_cache[index]
                return value
        except Exception as err:
            logger >> "Hit an exception: " + str(err)
            return None
