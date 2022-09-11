import copy

class History:
    def __init__ (self, *args, save = False):
        self.attrs = args
        self.save = save

    def __call__ (self, cls):
        cls._new_items = []
        this = self

        oGetter = cls.__getattribute__
        def getter (self, attr):
            if attr == "collect_new":
                items_to_return = self._new_items
                self._new_items = [] 
                return items_to_return
            else:
                return oGetter (self, attr)
        cls.__getattribute__ = getter

        oSetter = cls.__setattr__
        def setter (self, attr, value):
            if ((this.attrs == "all")
                or 
                (attr in this.attrs)):
                    self._new_items.append((attr, copy.deepcopy(value) if this.save else value))
            return oSetter (self, attr, value)
        cls.__setattr__ = setter

        return cls