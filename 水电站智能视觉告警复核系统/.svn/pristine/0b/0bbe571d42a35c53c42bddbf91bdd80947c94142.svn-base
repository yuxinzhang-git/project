from datetime import datetime

# 事件
class Event:
    def __init__(self):
        self.events = set() # 支持多个事件同时发生

# 目标
class Object:
    def __init__(self, *args, **kwargs):
        self._label = kwargs.get('label')
        self._center = kwargs.get('center')
        self._xmin = kwargs.get('xmin')
        self._ymin = kwargs.get('ymin')
        self._xmax = kwargs.get('xmax')
        self._ymax = kwargs.get('ymax')

    def center(self):
        return self._center

    def label(self):
        return self._label

    def rectangle(self):
        return [self._xmin,self._ymin,self._xmax,self._ymax]

class Result:
    def __init__(self, i=0, filepath='', occur=datetime.now().isoformat()):
        self.id = i
        self.filepath = filepath
        self.occur = occur
        self.desc = ''
        self.labels = {}
        self.objects = []

    def AddLabel(self, k, v):
        self.labels[k] = v

    def SetDesc(self, desc):
        self.desc = desc

    def SetOccur(self, occur):
        self.occur = occur

    def Label(self, key):
        if key in self.labels:
            return self.labels[key]
        return None

    def Labels(self):
        return self.labels

    def AddObject(self, obj):
        self.objects.append(obj)

    def GetObjects(self, label):
        return [obj for obj in self.objects if obj.label() == label]

    def Dump(self):
        return {
            'id': self.id,
            'filepath': self.filepath,
            'occur': self.occur,
            'desc': self.desc,
            'results': self.labels,
        }