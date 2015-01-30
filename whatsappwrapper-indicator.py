#!/usr/bin/env python2
# -*- coding: utf-8 -*-

# Created on: 01/28/15


__author__ = 'karas84'


import Xlib
from Xlib import X, display
from Xlib.protocol.event import PropertyNotify
from gi.repository import Unity, GObject
import threading
import re
import subprocess
import sys
import os
import hashlib
import shutil

GObject.threads_init()

_NET_WM_NAME      = display.Display().intern_atom('_NET_WM_NAME')
_NET_CLIENT_LIST  = display.Display().intern_atom('_NET_CLIENT_LIST')
_NET_CLOSE_WINDOW = display.Display().intern_atom('_NET_CLOSE_WINDOW')

UTF8_STRING       = display.Display().intern_atom('UTF8_STRING')


class XTools(object):

    INSTANCE = None


    def __init__(self):
        if self.INSTANCE is not None:
            raise ValueError("An instantiation already exists!")

        # do your init stuff

        self.display = display.Display()
        self.root = self.display.screen().root


    @classmethod
    def Instance(cls):
        if cls.INSTANCE is None:
             cls.INSTANCE = XTools()

        return cls.INSTANCE


    def get_root(self):
        return self.root


    def get_display(self):
        return self.display


    def create_window_from_id(self, window_id):
        return self.display.create_resource_object('window', window_id)


    def get_client_list(self):
        return self.root.get_full_property(_NET_CLIENT_LIST, Xlib.X.AnyPropertyType).value


    def get_window_by_class_name(self, class_name):
        window = None
        for win in self.root.query_tree().children:
            if win.get_wm_class() is not None:
                if class_name in win.get_wm_class()[0] or class_name in win.get_wm_class()[1]:
                    window = self.display.create_resource_object('window', win.id)
                    break

        return window


    def get_client_by_class_name(self, class_name):
        window = None
        for win_id in self.get_client_list():
            try:
                win = self.create_window_from_id(win_id)
                wclass = win.get_wm_class()
                if wclass is not None and (class_name in wclass[0] or class_name in wclass[1]):
                    window = win
                    break
            except:
                pass

        return window



class XWindow(object):

    class WindowIsNone(Exception):
        def __init__(self):
            super(XWindow.WindowIsNone, self).__init__()


    def __init__(self, window):
        if window is None:
            raise WAWindow.WindowIsNone()

        self.XTools = XTools.Instance()
        self.window = window


    def click(self, button=1):
        self.XTools.mouse_down(self.window, button)
        self.XTools.mouse_up(self.window, button)


    def double_click(self, button=1):
        self.click(button)
        self.click(button)


    def close(self):
        close_message = Xlib.protocol.event.ClientMessage(window=self.window, client_type=_NET_CLOSE_WINDOW, data=(32,[0,0,0,0,0]))
        mask = (X.SubstructureRedirectMask | X.SubstructureNotifyMask)

        self.XTools.Instance().get_root().send_event(close_message, event_mask=mask)
        self.XTools.get_display().flush()


    def hide(self):
        Xlib.protocol.request.UnmapWindow(display=self.XTools.get_display().display, window=self.window.id)
        self.XTools.get_display().sync()


    def show(self):
        Xlib.protocol.request.MapWindow(display=self.XTools.get_display().display, window=self.window.id)
        self.XTools.get_display().sync()


    def get_title(self):
        return self.window.get_full_property(_NET_WM_NAME, UTF8_STRING).value


    def set_class(self, app_name, app_class):
        self.window.set_wm_class(app_name, app_class)
        self.XTools.get_display().sync()


    def set_app_name(self, app_class):
        class_name = app_class, str(self.window.get_wm_class()[1])
        self.window.set_wm_class(*class_name)
        self.XTools.get_display().sync()


    def set_app_class(self, app_name):
        class_name = str(self.window.get_wm_class()[0]), app_name
        self.window.set_wm_class(*class_name)
        self.XTools.get_display().sync()


    def next_event(self, instance=None, atom=None):
        ev = None
        while ev is None:
            ev = self.window.display.next_event()

            if atom is not None:
                ev = ev if hasattr(ev, 'atom') and ev.atom == atom else None

            if instance is not None:
                ev = ev if isinstance(ev, instance) else None

        return ev



class LocalInstaller(object):

    class RestartNeeded(Exception):

        def __init__(self):
            super(LocalInstaller.RestartNeeded, self).__init__()


    INSTANCE = None


    ICON_DATA = """iVBORw0KGgoAAAANSUhEUgAAAQAAAAEACAYAAABccqhmAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH3wEXCzcz/JBsDwAAIABJREFUeNrsfXecHMWV//dVz8zmXe0KS0gCSQgBIiMQwYBMEthgog0cxjacAYMx6QwYMHC2MTbncGcw/pE5MCCCST4nwGCDyBkBAiEQIBAIpJVWYdPMzkzX+/0xHaq7q8Ok
                lQTb+rR2pqe6u7q63qsXvu89YGQb2Ua2kW1kG9lGtpFtZBvZRraRbWQb2Ua2kW1kG9lGtpFtZBvZRrbP5kYjQ/CZfacEQFifhfJdaH7XbazsMuSzuo9sIwxgZBvmdycAGNYuAKSU3QCQtv6miMgQQhhElCIig6zNxxAYAJhZMjMDkMwspZQmMxeZ2QRg7wXrb9HaTeW79DGKkW2EAYxsVWz2ym0TdMb6nAbQaH3PAGjaeuutO4477rgtdtllly3H
                jRu36ejRozdua2sbl85kWn0v26J/gJkBIoAZBAITAwwwM7ttpDkwMLBi9eo1S7q7uz98++2337n33nvfePrpp7u7u7v7AQwByFu7+rlo/TV9jGFkG2EAI1vMyp4C0KDsjQAap0yZssGPfvSjnWfOnPmljTbaaMempqZOgAyABRERCCBrQS8t6aXPFo2XXrrymUuneIV/YrB1DWIARArVMjxfSuKCKaUsrlix4r033njj2VtuueWp2bNnvw/AZg5Z
                62/Okh4KitQwwhBGGMDnfoVPKQTfCKAJQMO4cePGXHXVVfvvscceh3R1dU0lorQwjLSPCO013VrFHZp3ZXv7N4vw1faBE3wThD0f9C3Uny2hAVKylCzzQ7mh/oULFz59zTXX/OX6669/w2IG6j6kMIQRCWGEAXxuVvmULboDaAbQMH369I2vueaab2y91VYHNDQ2jk6lU00uORBArCFW6zslIx0tUXvOJZAtPUQQv91Kzz/I+p8VxkAwTdMsFAr9
                3d3db9911133nH/++U8AGLAYgf03r9gVRpjBCAP4zBF9o0L0TXfeeefhBxxwwLGtra0T0+l0q3eZVlbqCm5YD+qpsDua65QYwtDQ0MqFCxc+e8YZZ9z65JNPvgtg0GIGg4rKMCIZjDCA9XaM05Zo32ztnU8++eQJO2y//SHNLS0ThBAGByiqTPItl9pDV3WNZlETyvPrJEFmAAC5XK532bLut6644rc3XXHF756zJIJ+hRnYksHINsIA1ulxNQBk
                iKiJmVsBtM2ZM+fEHXbY4fD29vbJRATmkQUtSjrI5XL9n3766euXXnrpDTfffPNLFjPoVewGxRGpYIQBrEubKuK3Ami44YYbDj788MNP7Orq2l4IMUL0FTKDgYGBnrfeemvOfvvtd21vb+/HRNTPzP0WMxiRCkYYwFonfGe133DDDSc88sgjZ06dOvWgxsbGjhGirx0jAIBPPvnkjbvvvvu2H/zgBw9atoJe629+hBGMMIDh3Gwxv4WZmy655JKZ
                J5544mkTJkzYHcDIal9/qWD1c889d/+sWbNuBNADYLXFCHIjjGCEAdSb8BssMb/5jjvu+NqBBx74/VGjRm06QvTDzwiYGa+88sqfjz322Oveeeed932MoDgySiMMoB6E33r//fcf8+Uvf/kHzc3NG0iWoM/8cPI6PWWICPPeeOOR751yytXPPPPMAgBrLPVgRCIYYQBV6/gNAFoAtN1+++1HHH744Rc2NTePZilLuinDwdA7K5M9wNYHVghIHXgb
                iu+nMQWMa53j/shwQTbk/MI2iteB+jqgYEIA7qseYwslqLZi3SSxu8DuvT2zibkECtKwwyD78Dxs6T9Sn4VcfBOpY+c7z3MJhhACL7/88t9OPfXU61988cWFAFbChSSPMIIRBlDW+GQswm+/4YYbDvzGN77x0+bm5jH2ZPNO/sRLlXWuRbrWdxVQSz4ycVGA6v2sY8rtbWbgQIJtvF60G96D6nPuq/QzSL7hEGKHIZHFWOwWPgSRGq8QwA3aHJE1
                iEdtv0tBTOoQCSHwzDPP3Pe9733vf+fNm/cugFUWI8ijBCwameAjQxA6LgZKoJ32iy+6+IvnnHvOrzo6OjYJ0/HD6N8HqnW/WyNPTAoJcER3uCJEjkq6QYIOf4Dkt4qJIYg8izRyBie4RwiGmazPvqESQuCvf/3r9UcfffRtuVzuY8tGMIgSwpBHGMDI5tHziaiBmdtnzZq16fXXX3/JJptssp+Usi6Dz3V/vbzOTDSutk2Vj8PMuPzyyy/64Q9/
                +CCA5RYj+FwbCkcYgF7c/8KDDz543Fe+8pUL60H469ID82fsTvHaF6Gnp2fxt4877ryHHnzwNSLqYea+z6taMMIA3FW/iZlHnXnmmTN+85vf3JFOpZr4M/nC3YxhRGErpVcU58+glCyEwJw5c+469NBDr+nr6/tQUQs+V/DizzsDsFf91vb29vHPP//8JVtsscUR66sv38oEAjBQ5CIKMo8iCijIPIZkHt1Dn2BpdgmWDy1Db3EVegtrYHIRA2Y/
                TDbRbLTCIIH21Ci0ptsxKt2JDRsmYGzTBLSnOpAWGaREBhmkkRYZh5lwqO6+7m9SSvmd73znlNmzZz8PYBmAPpS8BXKEAXzGV32UMPtdF1xwwe6XXXbZXTUj/Fq5yyOuYxsTCzKPAufRPbQUT6x4GC+ufBKvrn4ROZmFQQZSlIIgA4IMi0EQhOKKDBogSfnGpX8MMEsUUYRkCVMWUeACNm2Zhp06d8MXR++D7Tp2QrPRijSlYVCqOqkh4fiVXJdU
                9cALITB//vwnpk+ffnE+n/8IJVRh9vNgG/g8MgA7PLcFwJh33nnnV1OnTj3MJn57Uun84vYcY3LkZNffr9BRwOdeIyYgWSIv83ij92Xc8/EteHrFozC5CEOkYFAKggSICILIIuOSmG9/tp+eFFGfKMTFBxef4PJFdv+xDXVmSGaYXIQpTRTkECY2b4pDxh+Ng8Ydia70aJf5VDUGrPQXCuuiqniv2t40zcLhhx9+wgMPPDAXQDdKIKL8Z1kloM8h
                8TcA6Dz44IO3uv/++/5qGEYTK77sEkHb/mRleik58oKZb1xmUZqr1uS0Q341iBgLO+RwC4enkJeDFDmPfy37O27+4PdYPPgeUiKDFAkQGSVCt4je7ikRRaoI9qMSlUMgHJsAhJnBkNZfWJKCCVMWYZCBWWMPxYmbnInxjRMdvz0U5AGxl6htUJUn65ACeYKDMSDFzalRRSxAgosP8GcwIgVyUGL+L7300l923XXXXwD4BCXswGcWSfh5YgC2X7/r
                ySefPHP33Xc/20GtaQg6OEwc6al2m6p59kKuG2EUN8jA4uz7+N3Cn+O5nsctkV3AEAJEorTKg7SE7pFYSIc5hIdJsAMxUkFA7m+E8JwFrDJC1gv8JUmBwSwhWaLIJlhKdKQ7ceKUs3DE+GMBpoC6EJYrwZ93kAPDGQWkUtoqQg+x/lXkcrlVra2tRwFYbEkDNm5ghAGsh1uaiNqYuaunZ+WfOjrat9FOiIqGjyP5gH72wpN/zxACb/e/icvmn4f3
                +98Gg2GIkt5uCAJIeIVdNYuvCrsld50cLhOGqx1w4HvwtxJDkGyiKE2wZGREBsdMPAnfnXI2WJakiGQjnPxdVDwOzOaFF1543m9+85tHACz9LKoEn3UGQAAyhmGMmjlz5rR//OMffzMMo3WdEEfIwBpzNf5z3ul4bdVLKHAeKSMNQQIGGZ4V3v7sErn7l0LINigh1C6QhwNqEGvZjguXVlQIdi0JJfuBRFGakMxoE204Y/ML8dXxR8I0150UgG++
                +ebD22+//cUAllgqwWfGS0CfceJvAtB1//33f/PQQw/9r3XheQ3DwB8X34z/ff936C2uRlqkIYThIXpblHcJP9yqqFcFaNgC9wKiOqvKRXh73V+TTRTNAgxKYcv27fBf21yDroYNYMq1r3739vZ+3NXV9Q1LJViJkpfAHGEA666+3wSg6/333/9/EydOPCR6EiuxJ9CHviQSlkNOEiRgwsQFr52MF1Y+jQIXkDbSMEhAkOFd5X1MwHNRClq9I41+
                RCFrc7USAGLTAquMQddelSLYIyWUvApFWUTBzGODhrE4e4ufYt+xB8I01y695fP5galTp37jk08+eUuxCxRHGMC6R/wtADp7enr+2tHRsa092cKIhX1WcddaTKGTW71W0B9tdUQY6M59inNfOwkLeuchJdJIGWlrtVcJ2HLXBa7hQ+tZK7u3GSW26NdfGlCxBREMwYc0tNUCu50qFUiWyBVzaEu145iJJ+CkTf/DZQRchjujdhKPPOuss866+uqr
                /2XZBfrXZ+PgZ40BpAC0ARjT19f3aGNj43h7FQRIcb8pLiYl0M4OrXVD093QWtfwxq5/HGS5/MgNRCNGilJYkluM8189GfN7X0dzugUpkSq57BQjHpWo3vsS/Lq98rvtWiz3pZVr1PNLQHHnh/3upg5grdHQbyRUmYU97qXPDCklhswcGkUjjpl4Er632bkoFotw3y9crwWV3gucuobKM5HvyZiC+Q3I7jM5AA/1OQzDwG23zb78+OOPuxnAp4px
                cIQBrMUtDaB92rRpU1599dV/GobR7g/FTT4kWnN9PPcRKXyS+xg/nncWXl71rEP4wlnlXWs9KYkvbCnAK/q7XbBr81VGvn7So+CSHU2+fvNiBPlHsAo1cYeH4NklNoUpqGqDLRUwMyQk8mYOTaIFx0/+Pv59ymkoFouhE5tDJ71PVlFxAZ7j5K4IyhUMQ+Dpp5++Z+bMmZdZxsE16yMT+KwwgAyA9uOPP376jTfe+KClBlRG8xUNosCg7MeP552F
                x7ofREu6FYawkHkKwftFfK11P0avL6tfRFqMX7VXT2IDSHohP4N2mIMPW6AyAba8B0PFLNpSo3DutEtw4LgjUDSLw0o5ggTefPPNR7fbbrvziGgJM6/CeuYmpM8I8Xdccskle1100UX3DHcgT8pI4Xfv/By3LroGGdGIdCrtIPNUote79VwR08MAqiR29inmpFT2jWMGHCEHUZiKEMQMJ1IXAjAJxVfIrJMWNIxASmSLg5jWtjV+us3vMLVlCxR5
                +BgBEWHRokXPb7bZZmcR0WJmXrk+MQH6DBB/++WXX37AmWeeeXvdY/cVqkgZKczp/gd+/PpZyMpBNBiNMIRwRX3fih+2+ldixHPgPuv62+OYOMEQDqTGWvgNgypT4FJAghOL0Ffow6ET/g0/3eq3w0tERFi8ePHcKVOmfF8I8aGU0sYK8AgDqDPxX3vttV89+eST/zCcLqKczOKi10/H490PoyXdCmHBdEuGPVEiTI8xj4LHIox5ek2eXHU0gb4b
                VePP0z7EBRp1HlBhdh8NZDjaeKioCKxKBm6wkgs3LqkFplnEkBzCpdv+Dl8d93UUZLHiSV6OukREWLJkybxJkyadIoT4QEq5XkgC6ysDSAPouPLKKw88/fTTb1WJP/DSaugqShkpPLDkflzw2qloTjcjJdJeA58gj+swSvxPMsH0kXpVztS4FbuWYkXwZUBN4as10IZAK0IlAKuFtKQBZglTSuTMLGZ0fhG/2uF6tBntKKVtV+OslOSpqlMAbiyC
                k2jU9v/Y7l6PB5M9QK0lS5a8Pnny5FOI6MP1QR2g9ZT4237961/vf+65595VcgXZL1RJoM3e2URqpBgroT2eHNpK0I+alJaArDmIM17+Nl5f8wqajEYIYXhEffKDdRTQjkP0FK9ke1B/iZZZL1AooMh7mlO0+KD0wyYAdaJrRZRQ0SJkhnnOtdKAM4ef7+ujCyCywMQaVcHeTVnEmvwq/G7HW7D/2ENQkIXI1+C/pycJsxIl6s1erLwGq91HH300
                d8qUKaf6mMAIA6jBZgDouOCCC/a47LLL/mK7f8qpV+994eG5fO0ZZ5CBF1c/jeOfOQQdDaOQEmk3BFej53vEe4InXDVGhowUtSlERPdiBKAFPOnv78MI2jH3ifL5R/j4lVBnl85ZiUCMeCesb6ElVgUr4BC/wiTUKMRscRB7j/kK/mu7q2GU6SCyGSeX4Rq2DIPPbb755qejBB1eZ12EtJ4Rf/vxxx+/w0033fRofXR+H3sgwn8v+Anu/OAmNKeb
                S6u+zsinAntUKSCB3lil9amKFxjPlqrTLLgsT2GA8SU82a8OqN4DW7IoBRwVMVTM4Z6Zj2JKy+aQXF+bERHhrbfe+td22213LoCPLSZQGGEAlW0CQNuMGTOmPvPMM8+hhPirEZnrOf6a4ioc/sRM5GS2pOsLUYrN9/vzrWPK19hhrZTwidZfm2017tkk5zIHocSqNCCZIbmIVbmV+MX2v8cRE46F5Pp6jYQQeOqpp/649957XwbgI5TyDa5TsQPG
                ejB3iIhaAIx/5513HjEMo72+HJHwVt887PevHZA2MjBE2km1FfTrB79761T5OC35f+eEzIKGkVdr+sS1GVl7L58XJDmPnFJoUI18Hj+KgUajCY8texhv9r6Gr2x4aB1CpbxMafLkydtMmjRp4C9/+ctCuDUIeIQBJCf+JmYevXz58vtbWlo2LWP0y7ZoEwnc8/GtOOOl49DZ0Gmh+WzCF24Aj6MGWJ8Di743DVgJ8x8hivgMceTk8osxCMRcJxKl
                ywnlwEjkjsaiFms0gBX4BIRaBUKehfzG3KBG5NpeFOOGfdw+lCIDHw0swp0f3oR/m3Q8UpSuaL74LSbabjNj+vTpu3/44YdvvPbaa93rGhNYl2VKO2X36EWLFl07YcKEQ8Jom33l5NSqnMxendw7N9lZOQwh8KPXTsPDn/4VGaMBQgjPyq+K4Dr3Xi1EdqqrC+6zpyJEnePPNyDtGoU2ZkBKmGwiWxzA3/Z6BuObJrmJXjXU6U9T5s/R4OaR9L5L
                BSVpjh8//vCenp43UAolzq4LTGBdniJpAJ3PP//8D3fcccdzpWT4E3fG5XVz3yZ5VgM3BqZ0HUEGDn/8S1iSXYy0ES7y+xN16AjNj+tP9AKI1lGKHw4uoqkZXBYziDY26mwDpc8Ao5TivD/fh6t3uR17jt7XJ9R4J1eg2Cp8c09TwlH9XCgW+1tbWg4C8B5KqcfXOkZArKPEbwBo/eUvf/mlHXfc8VyW3vRQjt/YMfTEzC+4zEOxD1nRZSZ2/8fm
                +CSG+J3XafnanOuQb8KqnF/pp5pK2yOxKDh99kBnWUMQrPzGviNeOZ01MNwgYXHA9abeCwoAptSWlTt7ewNvHF/g/k5vmX1Hg8/vgSYq56jj53bJK895DIDsTbDiZ+al9GsptGbaccaLx+PWD65zqytrJpdnxFkz9zioKamf06lU64oVK2YD2AhAO6o0Zn9WJQAC0ApgfG5oaB6VJIG6bHkMYc+HpoFIIG2UgniEEIre7nXvhaH4Yi3/fimBSHM8
                QUGBCpF6uoxHtVr3/dmEQ+8f1cQ/Dj51LblLMNpiGZACrJNKoCETOTOLb046Ceds+VNwHT0Er7322t932WWXCwF8iFJCkbWW6shYB4m/EUDHmjVrHkunUqPrdaN+sw97PLQVDGEgZaRLhjdBngw99oqvJ3A1is9NOhLpXqQkj89l/A07Hwl+C8fDceR94mCKSfuadG1y7TRJz2OGTzJRzY3kSjGK14BAEDDw6qqX8NHgIsza8KC61UTccMMNN1+x
                YsWCl1566dO1bRRc1ySANIDRH3300f+OGTPmoHrpoSsK3dj/kZ2QMTIwjBQECCSET0SkyNW9HN19ffbfr4PWwmSUwskSk6owZLYMg/liHnuM2Re/n3ELpCYhaTIpKtbBWGxoaDgQwNsolSrPfd5tAIYQovXGG288cOzYsQeVdDylGo9GqfLlj/G9IlXUY0f57yksx/4P74S0SMMQKcvlZiXuYFYkUXYj0nwYc1c95dDdtgGQr53nOr7v/t/850Td
                R9eWNW04YVsO6W+S/nBEP8OelWX4NT39Vgk85Jr+dGPOcel7J4An0AeWFJAxMnh62b9w2gvfhCChXNunjnC40ZL8UpUyb6zrpNasWXOXZQ9oQx1V3fVFAmgBsGEul3sTpfJdgZ564nb8wqvGAuss4dYJfbIXez20HVLCQMpIWZV2KGTlJy23j1rNvXaBoL0gLnde3PHyMhZXo9cntxNUmi+wFj4DDhgx9TEQKvH5lR13bWDFZSghpYm8WcDeYw/A
                b3e8AczSsxhFKVSJVDBrPj/3/PP37rXXXj9T7AHDWm9gXbEBNADoXL169cOpVGpsXXiaYMx8cGuQIKSNtAXhFZ7svHH+fTWzjt7OG53Dfy3JzDHfa3v1tbGEhT0he9pweP+JPe3UefBu79voKazAnl/Yr4KnjZ8IG2+88VZz5sx5evHixWul1sC6MFUNIUTnE0888R87z5hxEZfT84SNGzIN2PkvmyLHWaSNDAhwsP1qzr444q9e16/nerk+IH/q
                1ceEgUcczgYclVPJUyClhGQTueIQzt7qIhw3+ZR6DUu+Y1THAUNDQwtQqjyU/7wwAALQ0traOrmnp+c1Zq65TaIh04C9H9gOy/PdyBiZktgvfGI/yBPC65+vFED6BKXOQBx/jMuLlYWn0rcRSU5V0FpMHg9X9K9WF/GBaMq9XiURhDah+9+lB6fAKm6jBBYaLGRx/RfvxBdH71UXQnjzzTcf2Wmnnc61VIG+4VIF1rYKkAEwesWKFY8YhtFZ6/Ul
                YzTg6DkHYFH/e8gYDY6fP0rnD67oFMvCalGM8/O81U4uSBpsFOKutZN9kAqsskyDZOCeD2bjyMnHojVV+3i0cePGbTpv3rwXFyxYMKwVh9amBGAA6Pj73/9+4r777vtrDxFqlyC3u2yBZjypnEipFW8hwC6ddwHu/uBWNKQaYZDQuvrC3HlEFL78qb1J4uKLWFI9d2GPa7ruL56Hm3priUKKacfMsc+ophSDO7MswyAH3IVFWUC2kMWrhy5GChkr
                sInB7OZrpMB0UWQmuxQ6uQXZHSNlqUl+9OjR+w8ODi5Aqf5g3ZnA2nIDkmX4+8L+++//azvKy4F8gj2uF2iSPDgv0HbzwUaclb4/vPRvuPP9PyBjNIIgXMCOj8KYXGBIAEjGsLC+ULLVKl4I37msQGU9O/m+s7sCSSe1FSAtgcO5joImdr4jeA9VlA5r4wfgykCfvQg59bqROyl9dNq7/Qd8zwDFtQoVLc3663kR1cHrQIEFK+cQCBJeWDArJ9vz
                QH0XJVgxBdZHWxI0KIXGVBNmPTzDqSTF7L0Bk+uaJPbBl0mpeeDYHDyopczdd999IoDRKNW2pOFYhdfGlgbQtXTp0tmZTGZiVcIKBX/tKSzHkf86AM2ZZiuqTwnfDQvqcWk6dtzXPUv/Z9i+V9UqQ7F2AfKlIA/OBTsZqGtozBYH8VbvPBw0/mtlogXjB2jatGnbP/74408uXrx4OYbBKyDWynsBmk499dRtR40atUfVmrIvAEMIAzP/vh2a0k0g
                ElATUTirEauf/TtF4XscoS6qzedyr9mYcE37ZUt90W0izoMrKZRURgFDpPDPJQ/h/z6+y6nuXCtrTz6fx+zZs3/GzGNQwsbUdZFeGxJAJpPJjJkzZ87jlhGwdpyFCEfP+TJWFZYjZWRKK79QUnZZkoAI09vJjQVjjxlI/V2/8EUi9i0dL0ny3LjKPICafFOJcKSgfh+bhJjdSOmotgjpt42oY4q2L5D1/GHPE2rVD3t237txcz6ECCak6PfQ502B
                JtGImwHcVZLsZoYwcO+iO3DklGPRnhpVUwJpbW0d3dCQWfTYY48tqrdBcLiFNgFg1F133XXsYYcd9vtai3t/WXIPLnjpTDQYDTCEYbn7hNfoR8HoOAAhTEHNI0BWtB4nILM4nBhFTPekq0UcdjAqfU85KYSS5PiO62/YfZP2O8xsSTFsw3tenHfAo49TuFFQMpfiBmQReTOPeYd/DKqxB5uZ883NzfuhFCuwsl6qwLBKAETUOGnSpAnXXXfd3z1l
                vDylnDmQfcUxxPiLRrAbitpTXI7DH9kXrek2GMIACQJIWAF73gy+waUsWqcnnaGhGt2YI5Z9xLSNo/lKeEtceq84fsMJ+GFEvxlIXmOgXKyAB5+t5hwI9oXt5T3i3mwnlYHrdXq/byEO2uhwK9Mw+STIGOAXe4uPKPPd2G677XL33nvvvHpKAcMpARgARr3wwgv/uc0225zliFhcvqPKSfLDbgDAdv+3MUjAyeDrED0RhF2oQ2f00xXioIQGv3XA
                8FVNfMC6buurG24wRhTQ/c6BUuUlkJCUEv35Ply/553Y+wv7e4yCYXEp9mLG8BajcVWpUrt0Oo3JkycfuGTJkldRyiBU87Tiw2kEbJg1a9bG06dPP8vDnUPpPyKxg1JJQpDAVQt+A5MlDCpF9zlKHaswb/JlknGLdqg+MtWr42HUvkw0kKygxRDin1KuFbOz5jP73Fe6NuT7y2XcU+cei/qNrfuUc05VYyDjxyjps/jdf1HXtOcQa46BXSGBrCwC
                TekWHD/na8jxoGdpYa04okSoeqwaylfrS6FQxG233XYigC6U3OY154fDxcwNAJ3z58+/YvLkyd+s5YWX5BZjj79ug1ENnY7oL2y9Xyhgn2DqXTdkM1DKBsmLbmiildXzJBhDsoCeQh8GzSHXN622sSZEq9GIsZlRaDTS0UZkijAuU8UG6EQzw9HWkmYeJs15ScYzzioKX6YhX3WxSNOEIs6Hl1kCWAbDTm3idewBUoKlREEWsPuYvXDTHvcgb9YO
                yp/JZDB9+vTD5s2b9yKAFbWWAoaLATQfe+yx2958883P1bKijxAC0+7bEIYQTlYfVfwPJvVQawWWkdE3JFV+lOXclBKLct3IyiI2b98MJ005CTuP3hmNqcbASS1GCzJGBk8tfwrnvHIO8uYApjaPq0o21mUPq1ikrqUsHjGWFd83ol1s+FWCzMLRqoCbZbgvvwbX7nk7Zo09sKbE8/rrrz+w2267nYdSnMAAaogeHw4GYAAYtWDBgisnTpx4bLRl
                TI3Bj24jSOCPH96G/3zxbDSkmyBCcP7kN/v7iJuVunVa4q+HgMdRAAAgAElEQVRg68734tPcKvx6x1/jh1v9sOzzD3z0QDzVPQdTmzfUAE1qQ41cj5IYVRFsWAVDXZQ/EBb7X0lnK2ECfqiwdLIJDeHdo3tg162siRSQTmObbbc9dMGCBS+jlD2oZlLAcNgAGr797W9PnTJlyrEuPNSX1J8VxZ5DjAPs9cyvyC/HmU9/F+lUg2Psg3p9J1efVy13
                4LvszW7raGVEGmhrsh0gvD/Yjcb0KPC3uCLiB4AH930QE5onY1VhQAOhpfB+cUifOfgZTGEmC/3zhx3j+HsFQEKkO4e014O2HQWuj8h3o4FGK88fda4H7q3MIXV+2ahSAQOCDPzoxbNgKAChoLbPnpuyhtmon4YKBdx6662nAhhVa1tAvSUAAWDU6/Ne/9WmUzY9Kdq2n9QZQGgwMjjm8UPw4vJnrBBfUuL7vbBf/5rhlHlWA4vgK+6pWSjivFkE
                wgfZ5dhh9M6Ys/+cqmrhAUDPUA++8McvYLtRExOpHGGqeBQqoRxTAiPaQ4eIeyYpSMQxEzQJugJIhjCIBGyF9cn/GyvlyVmtP2hiVbYHzxw6Hxs1TUyWuzXEHaY2S6fTaGxs/LKU8nXLFlCsFYHWc8vMnDlzo2lbbHFSpbYoXxYlAIyXVj6Hx5c8ghSlfFYhlZ2TN5hIgXx6fyM3EYTHxaME1jgv2a/7wVnSFg/2YErrFjUhfgDYoHED7DduP6zM
                90d4ATgQWOK29ef3c5cwnZeBfcscR3ghvOPKyjnexBpQk2z434VnnMNFLo7wbLBG/PDDisGsDwQK+csh3gQ/VNnJTad4FggAsUB7ZhTOePoENKeakxlkmWObFQoFPD5nzsmKFLDOSwAEoOOpp5764fTp0y+smTUx3Yxt7tsY/cU+pOxCHkIp2R3i8ydFRSDNUkhE4QCZsOXK+r17aA1SqTZ8/PWPtDaFSrcFaxZgqz9the06J2q9B94ljlX/aIVh
                ylVa7xIkQqnMthBSDyEpqLCMPqrFTsgX38uSA9dyFgO4pchLBsFeXD/zduy/4UG1pKliS0vLTJQqC9UEHVhPCSANoH3GjBnn1/Ki9354J5Znu2EIw3m5nsy7NqhCBle/EnIwuLS4WWJ92qJ6TM1Qq/zeW8iie6gXbx+2oCYGRHXbctSW2KJzC/QVctrsv96ly7dmJIqU4djMxmoINoecz5rrxbYNyRisPa55Hg7pP/veLaOMZwYH5lIJi8BKzL5q
                AFRAAQp3ESA0p1rw45d+iOaG5tqtqESp//u//zueiDpQoyzC9WIABKDxz3/+88FSSqN8hq9f7RpSDTj76e+hMdUEYuGAM6RjWPRmhPHkEpC+dw99tJjdRnLpnDBQjmTAlIzFa1bgnSPeRovRorUOV2VUZ8YZW5yBpdmVHiCTlBxHu4FdxnznCBE4jnZQBm+JVy/ij5dzfc93WUYUoTpPJMKBQz5QkY3oEyTQPbgU18z/Xe2cLMzYfffdj2DmNpTy
                BYh1lQEIAJk99tjjNLuuHysrpzbPvoqOsmMB2EvF//vONRiSuVKudmIlypdD/zm/EoMhXSAH2MkCqz/PPkf/TwB4p/8T3L7f7disbfOAuy7MX1zuftqWpyHPjIIsBp9J809aKUasp/U+T8R3jhxDru4fJzyW9Hf2P3P0d7u9pITP658X5F45dM7YyVwcozKhIdWI377+CzQ3NisCmqJksBcByDGGRwDo6OgYe/bZZ89EqZZA1bUF6xIMJIRo+slP
                frLLvvvue7Ya9EMxpbOitsZ0I474xwFIGW5BDzhlvLzAH5/cpDV5xAdqxPj6c2swY4Mv4n92/h+Y0qxb9R8CYfHAYsxdMRctqYYE4zecWfrrdc11YdPlFqQQuqSg79L60F/ohwEDM0bvErQ7IcwToBajZU+9Cyklttpqq3FXXnnlAyglD81X95T1Ef9HLViw4HcbbbTRt8tz8YVvt7x3I37y4rloybRagB/hhPCScN1/HvdOBJy3UoK1ufeClZ9i
                5fEr0ZHuqPtUXDK4BBPvmIitRk+oiYehWhLnGk2eKBTxusCeWFN6Wlew1M0o7E1TJyXDlEWkKY13j12OgewAapGNUQiB5ubmfQAsqNYlWA8VIA2gddKkSceW4+KL2loaWvA/r/4CDUYpy48njZoNyCBoC4VpYkoCeQDLA/sAHw704KqZV6Ej1eGgwKSUVYv7YfvGrRtj13G7YU0hW3G/q9mh+Y5qr+vFwlR/vYR9TwQSQrCQKCNYnN07Hr4y5Q7k
                XGBNvhc3vnUNOCjkV2wLeOyxx75LRO3VGgPrwQAaHnjggcOk5JqpF7ctvBk9ueVOnTZ1IPxWal02Vy6jJl/cbkqJbD6PE6ae4EyIUPWjRptpmjh3m3OwdHCl8pwxDEdy3RiSDXqp6lzUt3+JxkiL7fDbp/RtA/PLWgA83hJLhWs0GvE/c3+O1nRrzYyBW2+99X7M3IIqkYG1ZgACQHr77bf/t8j66hzu7g2s/pkWXPn6b9CcbvUm9fDr+Ep0l8rZ
                fUKay6FZw9HtCK+I1eOjgZW4Ze9bkDEyGM7tyE2ORFo0IS+LnhUmuDp7E16Er4YcWM09r4Y5VKIKGDwRB2eNF/qC/eRAv/39CojrgTvoowg44v7e+eJKAeH9V3AXVJJE3RJybtzKstwyPL38iZrNh7a2trG77bbb5ijlDUytKwwg3dzcvMHorq49K7E8BKLXGHi2+2m8ufItCCJPuBB7fH0q8bMTG+/4byU86cRVHy/7skOy4i9ijb8sl8/jqMlH
                OSJ/Eku/2sbvIdBJM9pzTMb5256HFdneyEq8/hUtvJIwIisE27531t4L2vsHy26HVz2Oq4YMD9JR3y+9BBgv+cX3ywvxpZBnst3LumuQj100phpx+hMnemIEIrVgjj5umiZuvPHGk1FlZeFaM4CGf/7zn8cUTekdcOgHWIVqupVa3eNpkcIvX/kZ2tKNpdx+VjCIJ5AFIcEmqs8bvoy+9gslZdLAC1fV6YirhgZw1NSjkKZ0LGYhDNcQxjTizjHZ
                xCnTTkFvNuf1USt9lYzocYnQx0PPCUPpyojzEZE5OMn9EXJvLuP8uGujjLHiZIFhkr0eBFcKKAUKLR74AAVRCGc6qouT9AyaFUDV+PHjdwLQCqCxUjWglgxAAMhMmTLlELbKmoUbkPTCll9oN4WJRz9+2EL9+RFXikjIQQSf6r9W2YWtF3rFSWV1gSoJeIl0ebYP1+x+TUU6m+6Yzm4QxVDGNY/DgZMPwur8oPc5nbr3GgSfOz31q7Z08RHuWNrl
                SqQibfmkCPIyeJayxBWk976sB9T7kH4ckLjY8y6lNxGHlFoEok6SUJGANjrU0xdZmhMl6vXd14OIglZaKRUHsa7hQ2ko6YRAREhRCqfM+fcgFZACBFB0VNXAqFNDGhsaOw444IAtATRXqgbUkgGkAbR3dHTMqKQitW7e/+LlnyEljFJlH+m69NgX9BOs9gJNsAcpwT8RqbYke4+rPl4TaE21Bog0TKQPW/HDztX9pu6FYgHnb38eugd6vc+JkCAW
                61lKz0R6dB+8YwLPGJG3am4UWk+tsqMG5Vh9kJLDEYAyWN3H+468fnYGKWJ/NAoQMfn/PaHREchHx84UuAdpYpzJjTZ144phiBQeW/IPNKWbgxiCCtxlpjRx+eWXn1CNGpCqFfUTUeaJx584yp/xp1I/bGumFfe/f6cT7stkc0IlqSJx8sQWSfExpEoBrl0iW8xj7432hgHDkxIqCRMIW+V1f3UZkdVtr3F7YVRjJ4aKBaQNI8Ezszbnffme83Ld
                V6zMb1ZQcuW9m+h4oxpgIsrJUEQaIyQHsvp5y7vBjSEgEHJmDo8ufQRfHL1HTZ5h3LhxO1iGwAxKlYTKumCtJABi5symUzc9JJDOu8J38lbvW3h/zWIICA+4x1lVlEj8uCowAEVXnIF3tXKkAGXFWJUbxMXTLy6zFFS8LSBKRdB9LhaL+M2uv8bybG/tq/DI+MpI5eDpa1LZp7z4pZpUNIIs73zdvIPPHmDP1ZRI48wnTqlZNqZMJjOqpaVlLEqx
                AWW73mvFAFIAjLa2tp2qRqpZFtSLn7sALemUm0nSW/lRsUSVE9WRsEaURlbMFfLYfezuVfmldd6AMFUh7LNkia9N+hqyuUINqBLlU1dVFChr1KbO10YNnh9eC6LtFTBIoHvwU2QyNQvpx3333Xe0ZQxMrS0GkL7qqqv2FEI0AvBYNVW/vN9955hd1Kg9AlobWvH80qdKab5tn6ry11VbKbwir88IKVVrf8B6ywlQZQTi4cO8RzHSzkwnTtj6BKzM
                DTh9qxTtVl6bcnbWjmGScY7vT7XXTrZLJEEHalKHIRxZSCQgwbjtnT9ocBMcqHXpwXewz1TOpbk7Y8aMAyw1IL22GEDmoIMOOto0Ta+l3mEC/uRtlgDPdqCDYuFlYG7PK1ieXenow8RWGW1d1hvERd4pvyN+ZdYj1ySIUfMkmlGivz9xqbrlzTzO3u5srM4OBhCQlaDdkrcpZ0eNz5d17GvtEaPM3uIS6jwzhMBPX7hIERQsKYHJmaPk9zhANZB6
                PV/pdLrL8gQ0lEvTtWAAwhb/o20aFEBihTW9+LkL0ZQynPz+2hz9HG9CqQ6ey4q1VWJM85gSx/Vh/msdAxAHCrK/b92xNTZq2xi5Yh6fj23diTiMnVesR7bZvgFDGFgztBKZdMbjAWSEoyiZQ2Y7A8IwMkcdddTWldgBasEAUgAyTU1NUytxZfh/acm04PUVc71ZVZ1V3CsuySguLSvHtEvf8ULRxBbtW2hffsVRhRocQDn2kyFzCLfteyu6B3qH
                Hcuvni/XwXgDWadry5i55jDqsDgHp9goAZB4eMk/kpmU4/iNlLjwwguPqgQPUBMGMHv27P1qFaa6qrgaywa7naq+Jb3JFn+Ehym4YZkazDfpdLBglVjyGP5cLqzKHEU2sVHrRonF9yTEHOfuS3L9XTfYFWZenXw695TXphlwc3FyzL56DdLMTeZAOHyslMYh7dyw22BbjsCOsC4rGoJ/CQiUgPNa9n0YAKU/7LHuB5T1YHk5O2KV3QzUhkjjomcS
                ZstLQFpTpkzZFRXEBdSCAWRmzpx5uKfabxXbL1/6L6RJJW4VWy0DUVqOPCA1eHXpx3+71/SsYNa9JPwZdi1pQDK6GroixXL7+SuNEVBLTdnXivMiGGTg2lnXYllfXzByDazNX6fmSvS0k/H6r3qNsMg5VT9NoksjpJ2D3EOwLbSRehrEYkQaYNeVrEFN+p/Xf33p+83314NkhF96td8d4d01bydL3ppsa6rEDlAtAxAAUi0tLVtXAxmxB1yQwJ/f
                /xPSRsoSj8njqXKs/5wAHw49qiw035yyhHlslhbTSIt0Ir2wXJXA7wYsJ7RYssShEw/FUL7glXjCVr4kRT04BsvPEfECiCkeEnb9JPdDMk+utk+6+1CwrUzSL0QXQAl4CXweQbWYiCDGoOyvxCwVEHeEEOkddthhAkpxAcPGAAwAlE6nN/bHSqsd1ObTBzwuPAKhpbEFywaXQDiD5A8Otd6SjVVXMrUiLHNvRF47j2OJfTnwlJWMQMgWssn0xDKN
                goj1YkTvnZlOx1/FupUr5NkA/YoVlo/Pf17AKefjrqzJoKy9Pgf7F3hvrFtZEzgIddmB/Th95R7EwXgA7XMGC00gPrOpT08AkCKBa9+8VjHwKUFBWregJtxdmQuXXnrpARYDMIaNAcyaNWuiYRgtugAdr/jjBXT6w3kBxpsr30SukHOq9bJSptnjRfAVhtAh/+KKSuhx46Rta5DAx/0fl20hHo70XQTyYOmTlPxGTKGMJOdVk+k3KmVPkpLolWB4
                kLC/FWccjsJXKYYpTzZxErj6tat89gb213DzAOA8bnV48zDsvPPO+1qqQGI7QLWxAKmf/vSns8L0/7BCS7qsaAzgqteughB28lC2/reJqiS3MSV1JtZuMwRh4eqFia35tXFDJtt68j2A4a85P7IN1xY25sGkKd5M1XaEYE9uBSRMiJC1mEMMnLqttbVlvOIJSJR8sFoGkJ4yZcq+5a50HLKSPfTBg0iRcGNXPFZrJel6FCepCwMQWLhqYaxlfrg3
                Qxi4et7VaG5Ir9V+JH3ntJ7dI/H1krhRNFIPgZAWQJ7yaOTGqvtrmtKwVIBMUuqoRgUgAEZjY+OUWgx2Y7oRPUMrQIJKaj6RJ1KyJA9QZOqosKSN1e8UusIOxyoftvUWevGLZ3+BUc0tWtjqurRjPbwH6nlPa9oIIjz68aM1WxMmTZo02mIAiWi7GgYgSsZH0VWLnptkIlvod9BSSQJ4mBEojMkRiSfKCQhRz3FgmQKJqv4krSlfjRSREin8cu4v
                0dSUcvpYvyCaiJJfFe5c4+vBTspRw75qU56FpC7juGeF73079iXCda9fV7OF5Pzzz99luBiAASBjCNFZkXjlm/RzlsxxVAEZwjH16Zj9cg7FcGmKCCrhUM6eEgKL+hclstqH+fB1rr9KPQCL+hfht8//FqOaWwLBK7Jc6QbxATGyTqtrtau22j/13csaXFsnucuQ34NtyRf+QnoVgwTmfDSnZirczJkzd0MZmYKrYgCnn376VAvS5nHtgcONFmoq
                bfXoXQvugiC/+zCk2CUSmLw5iQncZ2WNmDItDRlc/vLlNQ8IqmSTJDHznpkY1d7keU6ypj5FAWA44diwkmZMYRPkczPGuRM4ur539LvkiHfMbn88RV/V/qpSQcjzcoQLgn3PC819wtwDrLhmdO5M/zJW4HyEYTG+fLj9beONN97WYgCpejMA8fWvH7mzZFnylBN7ou785RTssF9i+PLwlX5/4uMnICKIyzP0UWAPGdQeJCsJMzn6GmFFMxvTGdw0
                7yZIyLVK/GkjjUP/dhj6i6vRmE5rnp0iIbBAgsSfnCBBKGuuhZg2iAHaRF0P4f0FooBAFPkciAAzwZcs1k0cE5JSDEHAD2tqgbhQ4pKdyzCAPArOfUjFyQSKkcLLWB0mU6KdTCYziogah4MBpCZPnjS9RA8cWO29FXp9sczMjkhEDKQohRXZ5SDhtfJ7WIgD2Y0xxMakWIsTRREi2tkCiwlzWEJRdXtapHH+s+fjiSWPYVRrU1ANouB4xD4jh38P
                M2Br33OE+Bx4RzHvMCYjthZph5DnI901NCg+/2/e9hQoN6D6373qKSd+BiKAWCBFpfJv7vpPniQigXwa2ndWosGiaYKIMoorsH4qQFtb2xbsKYFQvjOQAaTTaeRl3vJbSA1bV2dbCI6ew7P5utlfQww0MtzYo14vk0rhsSWP1UQNKNelaJCB2xfejiteuAJj2tusEuHheHvE/GUfak/3PSxnvxqbH1iNQsbQn9paF3WJmNgBrSHOj9WXHFuXgDWo
                H12GYvUYa+JNWJs9ComfwR4/IuBfH/5TmVfRRcQ49CBDmial02kbDCTqxQAIgEilUhvEMPVkOi0kTC7Y6Ahvnb+waLVyreiE8BwClIxdtbU04LuPfDcc/OEz+EV5DHRW31BLMANzV87FCX8/ARt0tWiVkHImS9K2HKGOJb1P1P0JwYSfnOA96Gr/sOZdMpJJMxzjuvev/GURZqB/5Ga3Urr88IePVO8JsITqsWPHJk4PlqriVsTMzbVwX7zf+z6k
                tLL7svvXQQFyqdIA+YhFJSzJnIybceUMyyBC98AKZGUWjdSYaHVP6jaMGsdPcp9gjzv2QGdnU6kicmh5rDAGGyIKV8UE6sOEkr4brvF9kpQNo6hxYo48rupMdpSjLS0QgGeXPOtku65crCz9OeSQQyZeddVVL1kLvFkvCcAAUfXwJQAvfPqCE/OvxuT7i6hHTTAqdwLFxq7rr5JpSOHWt28twZVr5LqJIv5+7se0m6dhVHsT0ikj4fzgRL9yWWMW
                l9CFQy3TSVbgtYFj5DJ+pwRtw2xLAcmHfLYEImRzWRRkoSbPteeee26KUn7AutkABABBJdhhqGEo6fbSpy95RDmPcUdT/KMWqaM9HkDoztWnx+5obsS5/zwXJsxQwk2a8juuXWtDK3a+fRe0tzaWiF8JR49+Pko0Puq1UOY1g9cjzXUo0Nc4r5+/vawAwyMTHkfMNVDGfRJ6B8PThxNQMGuT3m3KlCmbwIrUracK0EJEKbdUFAF+DhdjBLMJaO6y
                ucpi71YBcD6RG/VLEUUc2Kvqa497zSykOa6/hufhU8DbvW9jWtu0RCW+KmUCD3z4AJb0fYwvdLW4+QJ0eq+m/7rPYWYP3TOzo+1TvFXdN67qOWH3IdXiHWETIE3/oDmu/g177xQjMYa1RcS5qgdGfUfqM0bLCtYIEFCEiVokCx8zZsxG9TYCioMPPrhT1cMZvmWbvVl4vZgAAIq+88nAJ27aL58UIZ2VikPSfPmSd+hES/b+lWrIsOoW8od4Q+/D
                7mhtwiF/OsSqWVi/7cPeD2GkNP3RuNRY45LTGlFZf1z/mfSJLXxjC3hLZYUlaoFvjNnnsw0m1whP/xX2e+j9dHPGpwayTgoNG99gNHv4dRBemNRhNwZQ5KLmgsriwPF2GgbQ1ta2YVIJoGIbwM477zyabaJUSiax5eNnYg/7dGsp+pJ2MKNnsEeD+S2V9XXVJao8MsP3gsi2jKEE6ohUjDXHDUOge6Ab7/a9W9dgoEM3PRRmNnLx0PczBs/KlWBw
                k4ytzyWlzSsARGOBUeb9qzkvydghpn3c8yTBF1uUWkTRCjwLAp/IIQ3vQPpTjxEYzc3Noy0GUD834LRp08ayn11Dw05DjWy2uiBKxg+CJ5aPya3959arZV/9VcUPTLqcP95/Ur2OdW2Q7zqa++my47S1ZHDkX45CSqTqBvzpMrqw15S9kM0WYp+tnH+o6dXKu0tt7i2H5Qlq1icOGyFXSiYCBguDIPJzSnuOekUQZ4F1Ct/aQfMEIURKCFFfJGBX
                V1dnLVY5IlIKb4SvdhTDRanMSA8OWZ3UCMOo8zPpFN5dtRCvr369bhJAQRZwz1fvwUBf3krmiZE9LDJsXe5TjHRi20w+HfxUb0D3LaYUWGO9Vm2WjFQqVVcJQLS3t7fX0h2jJPHV054HvllZGatwHU0b6R+bfa6trRGH3X8YMqlMpMGvmq2BG/CjPX6ENf1ZgNZjmq3wna2/z1tee2JgVW5lIpRp3AyTLGEYRn3DgZubm2vCAEgQ3OVfJcUIEYB0
                5JtwJ13kGlB21TwG0ilCd7YbD330UN0c2QzGJbtdggnNEzGUL66/JEH4fIkpESIpacaCCVg5tKo2c4YZQghRVxuAYRg1KW8qSDj1/7SGlwTiO1UqDiQ0hlHE+aPaG/C1+78GKWRs1V/1Belgw2GowYHcAP502J/Q35MfEf9rsDPzOskf+4b6apbTzDJO188LIAwjU8tVLypfvYQ3dzuSil7D8J6JBNJpgZ8+99NA7QC12IefyHWEr7ZV04sDwOZt
                m+OHe/4Qvb25oLrJVYqpXBsxdl0WsUMr/K6FZ5Qhz1MwCzULNFMYANVFBUgZRroWWWhVLEGYRy0ZL9MgTyhcrK5Wz1J/b21rwJXPX4n5a+Z7CzwmqPQbwrkDW1EWcclul2Bi6yYYyprhz1zW4Iecz1Vedzg2WseuU4Nb5mU+0dyr5VYxA5BSmrVOwaorWOEPzaQKcrr5Q0gpNtdg8nx29ueWjgwOue8QNGeaA8xNJfpKcAP2+bl8Dg8d+RAG1+RL
                kkIN8+npMKtcr+vXKf8gD3OfWIcvrzQfIkp5MZLzJCX5TngkU92yAjMzFylxV8OrOLIV/eetgcABzAV8IlRsjjoOUTGSegsS/K62y2QElg8twwVPX+BRBZKU+tLBgckDrXbLjo1tGIubDrsJa1YNgYnqKqqubbNdVVilOon24Ij+JfR0IKS/zrxhDXGHyBHkVM+AA7hTpOrY1OAVSwDFYjHrD4Hk0K5qymBbk5qZy5B5gnh4LadI9Og1ttYz0N7e
                iCueuQIv9bwUawgME/vjmIUpTRwz9RgcteVRGOgbGn75dV0qP8BrQbSn6schbB40p5s9tEG+aNjQ8ykY2WC1ic1fV7EEkM/ns87KVOaY+3ViAln4fIRKCro7eJJA0Lqh37V1ZXDQPV+FkTac1b/kkXE5s33cLx3ojukYxFBxCDfsfwO6MmMwNGSun7r3cPWFa8BMdOJfHcahs7FT3yn2phtzVUvFS2U3tOaPLFmT68YA0NfXt7o2K2eJIIQ1qGSV
                THKYip0qmFw6t2qGQDi0T+7vajvrN1LlEFKITTlO8MUdAJrj+mPqb6m0gGnkcMzfjkFLpiVA3DYz8BO4jujV4wGmIYGXvv0isn0FSJO1/QvupBmf5Dviru35G3acKri33W8KeccR70yQd95o5hHZ7UjXb6udKO3Q3Z+Uc9W/FJxbnj4qbUFAZ0OnnsOR9xmh3NO5GCtz2WUAdTMCypUrV66qDQOQiqhDKoU6JcJLmVLIfYNQPpNN/NZnDv4GZ7AI
                xAqxKcfdduTUbVOv4//OyjHPbyA0t2bw4LsP4u737q7rAthutOOZf38GvSuHlJkZtUMzPsl3iru2d/aHHEcF91apQPf+I94ZlHPgO9fzGb7r+rgGQuaiE9Xqu6Yyj9X+qH1kVtoysGHLWFef58qlISEETNOsqwTAixYtWlaLSDjJDANGCAbaUxwwmV5FyQeqGtmWoqRIBto7G/Hvf/8OilSsowrM2LZjW9x4yI1YvTJXRsfXtiLPw3vJiosGJoTl
                UvVdZwCjVBWgumtysVhMNPEqlgDmzp3bU6t319HYYfFXdmUAJRe3V9wv/RgmgoeKW7EibPW72seUQcg0Afves6/HNVjrzWQT/7bpv+G0nU7DqtVZd8GMFOGpRmJ/fHso75TKuL/+PN/OIeK8f6favmcQ10iNUmBJEkhVXau3tGWz2VUAinWVAB588MFVtZrEY5vHWgVB3bdKQiFkEXgDeokrRMpDRLt67k2Naby+4pK7Om0AACAASURBVHX84qVf
                QAgR0ONrtUtI/GrPX+GgKQdhdW8uckzKfQaqsj1VSH2JzhPD+z51fat6fOC6Fw3UJsFMf39/N0rJQOtXHXj58uWrmDlZmZwYcWabL2zj5JBzM4xYepP6fdjW8trsDKCzowmXPHUJVhRW1FWoNqWJPx74R+y64W5Y05dbL8bnM7UzKpKfHAqVLhCoWoJauXLlJxYDqJsEIEvqOydTPGP40M4TdvZ685T8gETViVxJxTLU8Bz1uCBCe3sjdrp1J2TS
                mboyAckS/zzin9hh9I5Y05cdIcth3BHpGYlmBza6LU3pePLW2nC8ZyxevHhRvSUA225REyTKzhvubDFQDhhRHT9oLZh0yGe/usAJRTkKaesX89JpgUH0YZ9790FKpOrKBIqyiCePfhI7jpmB1X3ZEcpch3YnDFgnPAggY2Ti10vW8QRvLM1rr722CEChngxAApBElFUck0GmREkEFsK0rmkWYyMn9x+pHnwiCOdI5f/UawjlHlHtVLRA4B8n71db
                cwOe++Q5XDv/2rrZAuy9KIt4/MjHsf/EL2Pl6kFnXNe1f9mhIlatGcTK1Vn09Q/BLPKw3RvDcQ/fHCvhdISmL8BO43f0GL29OADSRgmSDydgU/vtt9/+dr2NgAAgTdPsUUE4UAAQbpwz6TutPGBrug2GSEESJ3O1EDz4Z61oFCZ72dcUpFfbNOd5DFLq9YWGu0W4J0Z3NuOcOeegu9Bdd0db0Szi3oPuxWnTT0fPmgEnq3KdZN2y2jKAFasHscfY
                vbDoux9i6alLccMBN6GNNsDKNVn0DebAnPB+SCJjB79TZS6N6sfIct+qc1gysM+kfcFSaqRTcjwPDg7BOsYOrbnHCOAlS5b0WgygriqAmcvlFqtETURuZVMFVKOCIBgqFLb0IgqFPDLUEIBaeqz8KgYEPlSbCpn2tFGYkg/XIXznkU7N0rnUdJINefumQyXa49PZ0YStbt4KDemGujMByRKX7XYZbj/4dqxcPQjTlOHPi2hEtd+lFiLsef+S/vjK
                1QO45oCrcd+B96HT6EQTmnDEpCPw5rfexOCZgzh7x/OwqjeL1b1ZSOZQWlRXP4p4n4H3SPo+V3wea51UITyKvX+tAJ79Ju3n1FTwygbK0qnOOwUt65uI3N/fP1RvBgAA5tKlS+eS8JbIIltfZ++KzAoR6Far9nQbPD4FRkB09ZpVws0upDPDcFDBJwagEfNtTksWMoEi7uH/P8zLbf9LCQMNjYSx141FykjVXR0gIhw68VAsOmUR+voLGBwqakG5
                pOkrxXjsw8Y66m//YB67jtsN35r6LW1fC4UCLtzxQvSd1oc7v/pH9PUV0LNmEFJCe28KIEj0Ij5HvBdEqAZIcJ5/LlIC1APZ4iMDJgNbd21dE6afSqWYmbPDwgAee+yxFwg+HDvBB+2NtwMwGNPH7OitnWZhAVz6lQEjm+5v6C6sdkJZxQV5YgN01xeK8SaALHU4MbuqAji2T40NaQxyH/a9f18M17ZBagP0ntGL0amxWNU3CNIYP/391KFm/eNC
                EW381yyaJgRn8PjRj8dLL1LiKxt9BStPXYnHj3kCuUHGijX9KJim9toi5v3H/R43h1Dl8YDBWU35zYgsNlvORqA8M+ctBoB6MoDiueee+0atoqKO2vJIKyLQsmjacfHWOAnN2g9UEImoE9vIlV7CrucG5fhEQvZaNjyBTBF9GNXahBeWPo9LX7502JiAWTAx/9vzcfK230N3Tz9MKfVidYyaEDe2uraSGav6snjrO28hXyijBh4DO4zaAcu+uwyv
                Hfc6Gsx2dK/qRz5frHlAHlXwWznzTufBY2agWA4GIAafs2L5Ass7Z9abAUgA/VLK/lp0/OApB3vLhjlBN7akpAlK8RMoeQMwwoJ1QAQh3O+2uK8uE2oUntrOIXL7mCArs7Ei7iUMrNmgsxW/fuHXeOSTRyCoeqSg2reoNv+9x3/j5eNeRs+aQfRn8yAhAv0OjB28wSwUEiQUFjC0YvUArtv/OnSluip+viktU/D+d97H2995Gxs2TsKyVf3I5osg
                IWoU0BR3LrTPSqQZG0dv936H8Aa5MYAtvrAFDKoNCvDVV199wWIAcjgYgJRS1gQS3JUZjQaj0SkXhhDcFCm+T4I3lJZijFI6Q5EnEAxBo52/HYUUQaWAkTKZoXhMZyu+9uev4d3+d6tOCJk0OEuyxLT2aVj9/dWYtdFXsKynF0Urw5saXaodpxjju/+9CQCr+gZwyNRDcPwWx1c9T5gZE5om4NVvvIoF/74AW3Vsj2UrejGYy0MQ1dSJETyXgsZS
                DpeCgq+DA7X/pGQcv83xNYmPIiJceeWVT5XDAKqVojqXL1/+t3Q6vXs1YhcDMMjA1NumotfsRsYyjgmLs3sI3U/snuQicMN+1WFWKviq7iWPrZKCfdJ9RshvYQMbFoimHjdNieVr+vHRdz9CV7rLyZGQJINQGJGEtfVfM22k8Uz3M9jnnn3QkE6hs605KKYmnCi6KswDuSGMbZiIt741H3kzH3i2sMrK/jb+Z7K/p0QKHw58iDPmnIGH338YrS0N
                aG1ucJJokO8BGMkr/0ZVEVb7GqyMxxqmWyJ+aWeKNkuF6gbzBSw47j2MTo0OeLE54psFm1HUWQKD5ahRo/YDMB/A8nobAQGgsHTp0meIvH6xoOefgkkbSCnNTaWotl033BWmyT5vIAdW+bCIViK97qpbtXXuqugVjQO2A8S4nuN0R/sRDEOgq70Zm9y0CQbNwVhxPo7wo9rqQEO7bLALek/txQ+mn4ulS3sxkB0KLfGdZDWx/+YLRZDZgNe++Sry
                Zt5nSwl/Fl2bsOxJJpvYqHkj/O2Qv2HBdxZg1kYHYunyXvRnc9AtwOrciXtXencnR7tJQ5iaF67CVrl7RlECnemuANjFKV6vGJYdirDRg2xjAErfhRAmgEFLAkgkU1TLAIr33nvvQ0IYrkGMvLoP+Sxtfl3dTghKRPj+Dt+HySiV7FV9m3Y2X08GFz/4yJvbQZuvAnqLsKCQEFLPTh5vggdPAE3GGYo+Bij9ANCQTqG1KYVJf5iELGfrqgLoNgMG
                Ltn5Erx78rvYbcMv4dOVa5DLF1yxOizjEunCZUtW/JX9g5j7zbkJhdHqnrFgFrBxy8a4+yt3463vvIWDJh2OpT296M8NOXOFRIJcJr53FpxLFDwGTShz0BHmVUGJwSyRohQE23Yo9tkTvIulMweZHE5GxI7XzTTNXgDZpB6AWqgAaQCdvb29nzBz1VaM9qZ2NPy/FBrShJRhAEQwlHx6kfny/GI8xTkea1KCIXIIy8lDYbcdHMpDcBPeP/49ZJDR
                qDkc+b0cXVorfoPRYDTg+e7ncdrjp+PVZXMxqqUJzQ0NsTUNHBWAGUt7evG3r/8N+47bN/b+lT5D1JYxMni3911c+uLPcfsbs9HS0oD2psaa3oOtOH7/Sw4r/qImh5VSIl/M4/Apx+LqmVfXpD8LFy7864wZM84B8CGARK6WaiUAE0CxWCx+XIsHyA5lsUHTGNhRxsLmps5f9nJf5feIbGGWwdAbUSgCkgEHjI2RGayc67G7+9qLqNXFt/rY/Wlp
                zMCkQWw1eyuYZEYmCK1m1Q8Vv0HIm3lMHz0drxz9Mh79+qPYomN7fNKzGgNDQ0F/uv95ibB0dS8u2+syfHnClxPdv9bEDwB5M4+JLRNxy75/wHsnvocjphyFT1euwVChoJdiwrKZIbm04OBFYgzOdv0Lkxnn73x+zSSja6+99u+WBJA4U2y1DEACkENDQwtr8RAFWcBuG34RRSmh5EBVqFt4tS4Pxbv2hmDYnvDJfwJBZIbQoIYiMj4411R2RGQh
                oeRZOtoaG9EvV2HrO7ZBgQvgtZTCK1fMYbcxu+G5rz+LF499EftM+DKWrFiDNdksJKs6qu3WEljWtxrHbX0cfjT9RyjIQlXW/mq9BUCp2s64pnH4w75/wNxvzYU0M8jmC+EonaRZZcL+Ig4NBAcSL5mwScsmtZFGmM0bb7xxPoAcylC6RC3oduHChQ/qst1Wsl24y4UoSFU/YSdREIj1WV0peex1qC6LkFRTa2EHgI6mRqwpLsfWd26NAhdCjWIe
                vEKYASoGL6A7X/2bLWaxTec2uP/L9+PTUz7F8VuchKWr12DFQF8JmWcR3LLe1fjS+H1wy6xbkDNzofcMM/ipf9UMSmFSQ5RxVE3Fbi8uW7Rvgfnfmu8iIZHAnpHEnUjhcw2BWAa3KlBbehSkWTMDSQ7AQFLRv6YMYJ999vlrrRjATmN2QlumBdJjCEQAbuwZVV2kGzj6zUU5hAXWLgewrLrtjY3oM3swdfZmGDAHYtWA0BTiMeJ/EiZgr6YdqQ5c
                vsfl4LMYF874MTbIbIQla1ajP8f4/rZn4F+H/Qu5Qi5W5E/CfPztk3gP4q47rmUcJoyaAFPKRNQeGjXodwdFzjWlBLDFLYrSxLkzzquZtLZq1aq3LQ9AHmWgCmqBPyyaprkin89/KoQYV+3F+gb7MLVjGt5eM9fRSVWPgOtQ9HqdyZEXgvn9k5vkGHrPfxKPd3229sZG9A0NYJNbN8H8b87HmIYxgQKkOl9/NXp11PlEBMkS2aEsztv+PPx4xo8B
                ozQU+XweQ8XqcsRU0veyDKMS6GrswrKhPqRq/O78puUgjoCtkmWlv9/f5vuuvb6KSlZEAvfdd9/9lgRQVhpqUZPnBmQ2m50HDeH5Q3KDmUK8KwMD+MGOZ2Oo6Fb/cwxlridUCSem2AAONaafolLDq/nloySEED2CEgYrIUT11JoJALQ3NKIhw5h4y0S82/8uDOGtOuRf8YXGc1IOfNgvzenOs+87VBzC0NAQhvJDvlDvynbd88Q9i/+cqASspdcq
                Kg4KUgPDKMIg6v8OslVLBkuJtGiGkMJ19TG80aRECkaFQoqC2JlA2DznnHOesNQAc20wgML8+fP/LAwj4L90CZsc0I/ju4SXiO3LHTvtWKSEYRlyFFt7ICg/OgtbXHhq5GcqPwcRl3lPivjdG+oKNGcaMKa1DdvM3gZPLH3CEzyiM5jFIQA9TDfkfJVoYl2AVfyetGR6TQyDBORkLjbMuVbWHIYK6ilRdJFNfHPL4xxUYAnco8Wiu+fZjECNM7Bm
                nCnNXgB9FgPAcDMAACjOmjXrT7bPnsG+LB5+hJQ3i5AqKxARBgYHMH3Mzq4dgGUQrJOAK6vHdLpaXPhmkvBR9TlEkvNQwW/W8cZ0GuM7R2HW/bNw3YLrnPyCSUTmqDbVnl/t70lF/mrdhUQEGMCq3CoYgpK9k4R7pFTgsAJL/Adw2W6/DJS1A2IiSUl/4NNPP31FMQDyWmEAAHIDAwNvBHXvCnyLLPEfO5yDbNHKaSBEwN3nMpcYN5uSXtzxBDp1
                ApXILjUNucO3oijfV7VK+JCOSQLp/TqAiE9ykBIGNh7dhdMePw3ffuzbiesNRInzUapBEi9CtRGKtT4/6hwAWJ7rdoBm3qQPEXqa9d3jmkZUMgXtKgXJEi2pDqRkbaL/hBD4+c9/PttiAObakgAkAHP58uX/qpVB5cipR6I13VySAiRbNQThyTQUWvDR/x49rkLSQzgDRR0pPLKPlOvZkyvMHRTldvTPFeghw8HnI0zuHI373rsbm9+xOcwE7z0u
                jiBstQ3zIujQbuWoGOX2oxKVQbct7V9qJeekSDcgdDTM3jwQntUfwYhVB8JufWYARVnA6dv/oDSva+GCKxQG77jjjtctD8BaYwAAkLv05z+fnU7VJrFB/2A/Zk08CFJKkAgxDiVZEUJXg/iVU0T+Liq6Zrn3ESHHQIQJ7Z1YXexGy/+2ojvfHcgpkGT1jGsTZhOIMzSqv/l98nEuwXIMheVKCP9c8k9kGkTEvHDHWATmm3KOSD4vXDuYBJHARTv9
                Z7lsMPSXgYGBRSih/xIHANWLAZh33nHHe4O53IeVPZc3LovB+Nmuv0B/oQDJEswyEGUZTCK8toteDu9WKijZjPEtHdj41o1x1fyrnBUyqTstzsCWBLyTxJUXRvxxhku1X7rPuv6rmHv/b3/+4M9ozzTXd6YwazP/SNPE5LbNMJDt1xIDaY/o/YNkMeE777zzNssAWFEV2lo7sdsXLFjwy/Hjx5/qe7OlZKEeIvU9WOA5Cc3pZnzxz9PxQd9CpI00
                hBPWZblyhCbteJjIat3aycQKN3qRWcVpI1E9A/sc5699fUIE9qCS8CDdOcFjDGBx7wpMadsUbx3zlgdhVm4wURRxJSH6sJj/qBwAYffX3dvPrHT3Vf/aW9pIY/O7NseguRwZI10yyTGBKGKsnTnCiTwYbE0ElXlJKSFZYmBoAHO+9hI2a97cySNpY9hYQ5UEglv0mksl6bn0twQolEMdHR27A1gEYPXalgAAYOiqq666LZ1Oe0V02MkL/CnBFbEK
                XhELBGSLgzhl69MwVMyVcqYrsGAiLguyK+ANAFLTgqseBmHhDeLAgMJ3roAurJiqcDAlyUnrfb7J7RugZ+gTNNzQgDfWvJFIVA7DEajH7e9RBkd/+zD/fBKjpdpOvbf9DOoxFbMQhQewZ/vC1QvRaKTd3LwUM9Zl1zb1zktYgT9Smuhq2ADbdWzn+PBZMRp71VavMdqT5EaxN/X19S20xP9cpeJvrRlA4fe///1b2Wz23aBQ71uJtKChIIDoxC1O
                RmumHUzsteghuY+GUQM/z3qydza1YmJbF3a6byfs9/f9YBiGVgQPE63L9eX7Q11r7bpL0oekKMDr3rwODWmj7DENmz/h88rNbWmbq/NmHqdtdzZyxVyE0J98MwwDt9xyy80AeisV/+uhAgBA2yuvvHL+ZpttdlEtLkYg/PqNn+PqN36LhnST1iimnwxecc5J2V1n6C4qFPjrcfHl2T7kiiYe/urD+NLYL8FkE5/XLUUp7Ph/O2LZ4AdoSqerYjjh
                4r+d9stVA6SUMKUJMOHT4/vQn6tJDl0Ui8W+zs7OLwH4AMCadUUCAICh75166h3pMgY5ep4zztv+4lJKKeZgWQ5d/TV/hT8Oq/pX33+intXpKL7NmKZ2jG/pwN5/3RvT7pmGIR6qSfbh9XE3ycTc5XPRlE7X5D0gpLYkfHMTKGUrOnjy12tG/ACwdOnSFy3f/xCqsH7XgwEUX3j++SU9PT2PxVk5E3dSCpy09fdhcgFqgQ4t+k+H2RFlaQzlahgh
                hR8QUzSCIrEkUTEGUfED/v6nDYGpo8ZidWEp2v/QjpOfOtlRCz4vmyCBAx88EBs0tVoSpGVDomBBGHdnhKH7XJ0W2iSVahVghgSDcd2Xbq5c7PadkEqlcMIJJ/zesv7nqxqbOoy3BFB44YUXbhbCcPtPXvu/Lm2ymm/f419kExds/xP0F7IISxgeZXajChJCU9nt/bEE4Sa/KNw/YspTef9PUBLN+tyRacbktg3wx/dno+WmVlzx5hXrFSOoBkz0
                +NLH8ciSRzCqsQW6mG8KNatGJQjXnefV0JgZRbOIAycehuzQoGvZJ73TT+cABNRcm6Vt9eo1Hz777LMLLQmgKkRRvVTUFICugf7+dxncpmYuJcf14lNj2f+k3qdOiRQunnsO7lx4C9KpjBeFlzBNVmRGXfXOrMvpXp7aQsNoayj3heeliSUDK9GWHoVLdroEp219GqSU+CxuWTOLzls7MaGlAxmRqp7hsFKZWnERsqXzl9xzpfTfpiwim89iyXF9
                MItFQAli182zgIs2QBIMYRh46KGH/ufrX//675n502olAKrjPGt98cUXz99yyy0vqpWFbFAOYOrdY9HZ2AUBASGCDMB2rZDGkx5o5/NI+AeFy/zs9W6E552PrTMQZsn25beH7/lsnIUuN0KwPWHILGDJ4Aq0Zbrwg63/AxdPvxhg1Aym6ieoWngEyrmOhMTo2aPRkhJoSzcFJnzo+CQ0/DG7DN82ANp1AqQ0MVTM4bBJR+OKXa+FrFFqZGbOt7W1
                7aYY/6q6sKgTA2AiGrr44ovDjYEVzIU2ox0/3P4iFGVeBwP0CO1AdD27qLz+YW3iPuvun6QMd+CcsAlO8c8Zls8/2J7RYKSwads4dKQFLnvtZ8jc3ICTnjoJ3blu1CrDUxLpqx7XWZ1fjY7bOtBkENrTTdr6h7rx4bL6YjNcdzrS/2/vy8OkqK6+f6eqe2Z69gUEZlgGREFxhbhBXoISFxTUqMSowQjGuPKqWTTmlcQowfB9MYk+fu7R15gIBqOT
                aAQFXEhUFJFFQQZkUWSAYWaYtaeXqnu/P2q7VV3V2/Q0M9L3eYYZqqurbt26Zz/nd4gAZmWuPjTp8YwRPwBs27ZtmW77dyMDgOu9qadKAEo+//zzRwcPHnxFpi6qkorRSwagyF8CnySDSHLdGK4bhTKrmGc3qNjbpoFWp94S7kRzdycmDpmEG8fegO+P/r4mTXUTIZkswnSPpaKae2UaSiThzb1vYurSqRhSWIEyXfIn+0JjAVitt5xMHgRjHIyr
                6I4EceO423HHcfNSBHX1ZkM+nw9jx449d9euXesAtCCN4p9saQAAwGRZjjz11FOP+JIpEEpyL/i4D78/4zEoLGKmXdobLnjDNnu6dRJle3k0gegxdCAlmWlGaVwXqUNX+EjCEYFSHFtRgy87P8O1//kB6E+Ea/9zLTYc3KBl1iE+nHdPjiWrAXjhA0qShDvX3omp/5qKkcUDUZ4XSGlt4ALtbnV75i6VmhwiapVmBmhpv8X+Evxq/II0EJ29z//y
                yy/f37Vr165MOP+yoQEYDKZ03759rxYXF09Kl/M5h9/nx8n/OBIhNQhZ8pvVWzzRpgOS9+71JI0/KVFDGbte3JXrgUdTAqByjpZIJxq72zG0ZBh+Mu7HmHPUHJTmlfYYoSeT5sWW1i2Ytvx8NHbvwciiI8BSJTwen1S1XhUUo4mIGoCR+NMebsWj//VnXFBzsccbIhePUJz3SoDf78eNN9z4/WeeeWYl57wJPcj+yyYDgCRJRQsXLpx0yy23vM5U
                1fVxSSiKMCoBtfoBsjoFE7TogV4UsbVzE857/ZsozS+HTLJrSDFtGzKZjp69bTOkcG7CU11PSO1hJCIElQgOhNvR0R3ClGFTMHfsXEwfNh15cl5WmYFhPhARgkoQv/j4F3hw44OoLqlAhb/IIXXjMFuBBl3JP04hkEbwOmPQHaecc0RZFEeVjMXK8z9AMNIlRL8cTWxhVZNxo7UnWQVAZMXMAABNTU0ba2trLwewB0AnMlT6mg0TVgZQ1tLSsio/
                P3+csdSu1rggrRJtzzwpD9e+/z28u/9t+IxKwUwxgGxsYiTuINwnfQX6Jm2NBNEYbkU4ouKSIy/FDWOux+RBk5Ev5/c6MyAihJQQHq1/FD9e/WOUFxRiaKAq7QYqqeIVmh2BHZKfcYbW0EGsvngThgZGJM3IEpq9Ph/uvffe6xcsWPAq5/wAgGjG1jJLKlrhvffeO/EnP/nJ8kxujm4exHF1w1GaVwLZEeMluHP9vsIAvi6OQwA4GOlCY7gV0SjD
                hSMvxC1jb8GpA05FWV5Zxu+5t3svnqh/AvesuwfF/gIMK6yETLJG/GlwUs55XC6cnONP8/qHoiH86Ni5uHPcr6FyJWPP3NzcvGn48OGXZVr6Z40B6FpAeWtr62q/3z86kxvwnZYVuOndHyDfV6BpAWI9v6sfgBIHgwHvoD9EAAAPky7VVeUebyRd1SBTKkWyz8SttW6NdKIx0oZwRMUxVcfgZ+N+hsmDJmNE0QgTxDRVadgUasLa5rWYt2Ee1uxb
                g/KCQtQEKmP8Pu5r6sy2iaP2O56TMx6TuGEjft0EYJxDYQrykYdPL/sKESWSMcLx+Xz49a/vvf7++zMv/bPJAEBEhbfddtuE3yxYsIpnMOtMlmRc8OZkfBXcpTkEbV5qF/InB3Vzsa85d2wGN8rmcWiMkqCceE1HeBKvxf3aVvYhT2IeqTRJicclvecqEaFLCaMx3I72aBBgwKmDTsXsI2dj0hGTUJlfiUJfIfKlfK21NVMRZmEElSD2de/DB00f
                YOmeZVi5bwUikQgK8vwYnF+OMl9hAgef17Pan4HzBJ2dOY95HxbhczPV11D928IHsfS8d3Fs6fHpOWs9RmNj47qRI0deCeAraN5/3i8ZgOELaG5uXlFQUHBywuVIuFraCQQgjDBOemUkCv2FkEg2vyp5hp+E2G5MN5fEabyxpMEF5yV5kk+iTECvJbDcovGzCuP1NUolQxFJkZA3a4ndYBrjDaphNEc60a4EtQawDC4FIkC+LKNYDqDUF0CxrtkZ
                GPqUBJtK9PxM6NfnyoI91H7o3zUZgE78YSWMOWNuwC+Om5+gISrBExHL5VSf7MPcuXNnPfnkkys4582Zlv7ZZgAgosCFF144dvHixR9zxu3SVIcN4uICWThiFsSTSGD65wQJGzrXYta/v4M8Kd/KeDOy2SxcJTNxKAbTy0sCx+xw5/nkctyxiZznmztVUDHJiQ9FzkIJ9+3q9HBzj/CSOAfuoh65zd8T88xDO+A8ptuTtfb24g8b/LqxLIzrIBrc
                e15e84t5NpveLnjcEzoFBOvB/j3OLN3DIH6VqZAgY9N3voLCFGuPErdZIeZcvZgAkcXo9TXbsWPHiuOPP/4mAA269Ee/ZgDQQstlO3fufGzQoEHfzbRn+Or3L8Hm1g2QSPb2ARD1irnceyOeGdFbrzCZGEW2Vi41bMSkHH4pnhNj98MC+mgLH8Tqi+oxJL86o0/t9/kw9dvfPn/VqlVroWX9Kb2xur4s72YGIHjBBRfMW79+/XcVJXPPxDnH1vbN
                Zp09R5KdcZPcQxnzq4lCMqkepIkqGXowac/7U4L7Z4jxJOWaSLaiI/H+SAqM1Mj8c+QAmOnGsJhAlEXwpyl/Q3V+TdohSK/xxvLlj69atWoreoD4m6xEzvaIbt68+cCLL754ayYv2s2DCCodJuKNCPrpmspr/F9Krj2UnEaSngAAIABJREFUlGy7L3j8FkFEJeG4FCc9OMlrxutP7/o5xbk/Umh6mcwc481LSuJ5KH46dtyUagPAg3Pva5E9DVgS
                9oXY8ANmd0utSY3KovivwWfivMEXZpz4ZVnGhRde+AyAg+hhuW9fZAAMQPSmm256N1OAFATCiv1L4ZcLLECROO2dXFuIGcd4Gln9lESLYO+WxAmgheL85sm2s03h/pQAish5nCeAL0rUtjkRvJHzXO5xPY/jnCN+uy8z285RL6n7YSxPFemZf5r6H2FRPD7xr1BYZv1yRIT77rvvFlVVG6DF/HsVyNGHQzPkiRMnVqmqmjSJO51atiNE+M3GuyDr
                MNAxfi83X1iaXpFsWMRJX4tS4pK95NntpetTz49ran9ie99uGpDgq7NgwQzQD8YZ2iIHseE7u0FcTrAvoTNIj3OIrF4VOhtqamr6dP78+W/p0l/pbUI8FAxABlD40EMP3W7Kb3J5YbaIgJktbUp8bq0c2tVWBJUgivNKPGHG7fsk/SRcygJ95XIVM+MTihfOjR/u5ULgiKx0X87QHQ3ijfM/RJmvXLuGDe3K0URFUCaM6xCRyzvWdrY/z4+ZM2f+
                DEATNLBP9nVkAP7BgweXjxgx4jwlqugNQ1wcdC64aYTYUBKB8NaBN1DgC+hxf6cGYPe2WbcgF57tFuJKRKJJYurbZ2bhPXHhXuRVJeYVP44XyXcWocQJQZlzSjQHL89h4so2+8T0c0UJSYTEGRHx3hHZCdetqahApJYQ0fNJOMXY8pbQ0RhAVI3gd6c/ijFFx1oMxNFFyjP7FF4YFdYZz/7vs/NXr15d39uOv0PNAPK/+c1vDlcUBaD0EVKNRZUk
                Cfdv/J8Y9d/gAFa6kOjYJoc+IKaUkqe+4L7VycNIcdcz7GF+sksIx5zs25uEe5MtjQkgx3EgFhpMrGq3b01zfhSLMRSrI5ErvBh31a9ipaz47NzGpJ3RByd7FVkZCestrH+CymdTQhuNgozuPAZQJ7cyAJ1qf1SN4rujZuHCmpm9UuwUDocbf/jDH74ILeTXI6jvvswAZACFv/3tbzMWATgQbkSX0omSvDKXrepuCHiZBoki7m7qOaVhHlAcM5oj
                MfwYuRAwPJ4+mTlSiuYIJeEC4HFNsATGFyV3f4JT9U6m5yC5r4dZ3mv4Abjp9FNUFSdUnox7Tvi/GcVLNObv9/sxefLkawDsg9bmO2sIrdlmAP6hQ4dW1NbWTotGoykvVKxDT8KqphUI+ApNvHfnF11lGKW32RMdz4QjMJnvuzMJr3I274v2ZioPJflOe1z7JOBFAPESB70cgtxElhIlvxHuU9QoBhQMwKLJ/9I6/GTST6H/fu655+avWbNmC3rY
                5qs/MID8M888szYaVeJvDCEL2JUodXPVJ/nw209/qWMDOhN/uJX2C2ciiAsseQYIIlvOO0rl7nFELmWTI6ShGSWaj3sb8thrcPCYvWGk3HLBSy/iDHJwKFxBQC7CW+etR/IRq3juCzK7Wxlz6Ozs2DF79uy/AWjOpupvjGzmAcgAAr/85S/nkuD4cHZG1VqJmz3AIWLdGl1cuP55Q/dudEXbbYRus1U5F7r5xjru4iLzxvk8VaInJBctowwREbn7
                mVK6GCWYN6Uw33RMkLhzjteMFHB4fLjLcRJqNYSqP8Hbr6hRFEgF+HDGVjDGbN4NErpe265sdvElITHJ7ugivdaBA5BlCdXV1Vfrqn9GUH77sgbgr6mpqRo1atR50WgUNiYQz9FHLhY9aQVA/2l+E4X+YlvDUFd1wWsTxxSopCClEnwPCWzX3mQCSUnXNK7fk2TctJmAmx2fLLqz0FDa6QgUpb0ZQTAkv6qg0FeM98/fYkl+G8EbF/YAYTfRad32
                scVA7rrrrh9Fo9EvddU/ikMwsskACq644oqjU7H943IT2Y8HNt8Ln45Ua2K0k5srTNgJjnZEJJGnumkeiqk4M9i7s7rP9b9xTY1kte7ktXOrQDlGA3XYnu51fTyRVyHu3HpashNzLTEnnye4jphP4lGDbYT6nN5+0+ZnUVTkVeCd8z6Boiq9Zuxt/OSTJQ888MDb0Lz+ERyikU1EoIHbtm17etiwYdMyccG94a9w9spTUJZXrncI8ugPINr7XAMU
                hYsmYHM0OkB/yEFUcNtbDo2Ap+DM7K0Xy1O8b6Lzenv+Xgwq6bBbAnBPq3MPFywArY0X4wwRJYyhhSOw7NurM4rq4xxdXV27qqqqLoBW5tuBXk737QsaQF51dXXVqFGjpmVCA5BIwqoDK1GcVwxJsnq6kFskwMj0JgInco0K2DYN6bXc3C1fIMZqtDsuk+Csvc1xeQpqdzrzoywxL0BM1U1OW3BmOTjfLxe4ihnn13H8w2oI48pPwpJvvYFwNNx7
                74fzUFVV1XcBHIBW43/IiD9bDIAA5N94443He6tUqcklv+zHI/W/0yr/XLu1ul3FKyvAoQoLGJHu4o7HJOnEEEYc/0YmVP54FfJ9E2k4vbr9RJa+yChiE6Ecn3HYQFrM9F5whKJBTB1yAR4+7Vk78Yt4HT3WfghE4FdeeeUsImrgnGc95HeoGIAEIP+KK753tQDMo6nUJuKP1RHASM20Za9x4W8CtnduRXO4ERX5lZZ6L/ZpJy+cOnFj2E+zfUPo
                XhxLVJSkNOTuBEqUkLCTcRRy2EM4bnY9IXEj0+zAiZC7b8CJr5pA4nsyCiGzmgSXDrchLAn2vmEKMIag0oU5o2/GHeN+rav9ljbJRTQjg70ILiBuupa48Cxk+Y1EtiEBdS/XLairq/uIc27Y/fxwYAB5gwYNGlBbO3Kaqqo2GzwWupsc8hoxdr0MCW83voFif4lu9zuAPsVogJuoJIq/yQTKIsdxch7g5H4iKC4RczfthJIHJ3FzhollD+RQdU0f
                qIOjUTLePC+PYRybI8b08Ej1N9trWe2bk1N/hLIwt3tyB7irmd2nf6LZ/CpCaggLJzyCGUMuRUSNCHOy54s4HTyOrQSxxoTg/FDbj5s2bXrx8ssvfxZaoU+oLxB/NhgAAci76667xpvNJXs6YdmHP217GDLJgnwRI7JkbThy2x3cjNW6yWuNi9uz552xJNM/IGwOK++d0sxoczIaL0jLBJRroz7H3BNhDIo2UMzaueD9wQMfEW6ck9vS9ThiicdD
                HUNsc06y+V1MF60Iq8jtj8KZ4QDUPP3ghNfOeh/VBcOgcHczPLZwLI3qUSLs27fvw5NPPvluAI3Q4v19o6daFhiABKBgxowZV2aqgGJbxxYcCO9FRX6laTaYElRwAjqh4J3eAC46jIggeZYRU5yNIZovyZoGyW4jnrDHQbouR9d0WY4E2TfJVgV4nSOq1KmQEXk6A201AVyEmLWr/KbnH5qzr7pgKP511uo0svtSF19tbW3bhg8f/gOd+Hsd4CMd
                Au1V9b+qqmrAiBEjzsvEekokYfm+V1HkKwFBsiQlOaWbkS1owHmR3s2XzIxAydAdiEBWFYglaRyufqsRhKVW2pLJXLgE2RBoLHVQikG9gXsiEwkZkdw9JGZlUAqMQmeERGSv8NPPlSTJ6nxrnCuRoDVZqDrGGtlMK5cOveL/naDKVhcdsqv6NpOMTA3K/mV75l1cZ69jbUQwT5WrCCkhXFX7Qyw7a036qb0pjHA43Dhw4MBLdbW/o68Rf29rAAQg
                //777z+de0FVu6GlkCssOwgEn+zDX3Y8CYkkXYJLMWaAkKRlk3Z2pCCKJ9LjgomSQ7v2ZGRm/ziHje52S4rfchtm9mPsXG0AFLY5Cv8SJXAzOnwv5G3Xu6+jFVePYVAxwKIuKppobtjg1L1VL+5k2OCuhM84g8IURNQI6qa8jREFR5r2vpu3P57TNf5BsUCZEFWiHaWlpdMB7IeW6dfniL+3GYAMoGDq1KkzbWEdckhoRzdgE6yB7HgZnHPUt23C
                /m5L/U9EPJQEYaeikvMYCZ+6kS+q30Q9g7lOnhOTvf9ATzz83D3Fibz8EpTaNd39HxSDuGNP5RVx+5hQx68iokZwdOk4/HXiq7ZMe9KjUMTJES1wIWln114hUhUD+0UExlh09OjRMwDsBtCKQ5jpdygZgL+4uLiqtrb2XEVVY3P6CTE2tyitHOnUkCQZr+15GcW+Il2F1nRwcqoMJDjvuOOYQ7q42e2xGaRGvJiBcRUcHBLJkCEBehciD1edK0ET
                eaus8eklmcyAeP4EM6c2RaZFKVptToDNxIQf/w66gBDj8Za6AVt4jjNd82JQVAUhpRtPnrEEp5RPsgGBGN5DcuwDMZnL6BBkwoGbf5PdEQxo4WzopiTATjn11Gl79+7diiyg+vZVBkAACh555JHJViVVD9UJWcaSXc9BIhmMc90McCLS2JmIaz68IGE43B2FDNxq+sijULmKy4Z9Hz8aeTuKpRJ82rkeN6y9An7ya0hEQtyQEsJ5xCccrxBhz0uI
                MlVm1LPv8Hgdk9x0Jm5FWWLeFVlIvYbUV7mKqBrBmNJxeOb0Ovjgi4X6osRzpRS0S1OASRKmTp16/saNGzfjEOf49+YbTlb9H7hz587nampqvp2JC37euQXnLz8NFYEqSCTpjizRqRXrTEumMYjNboSWFhphEcgk49pR/42ZNVcjIBVBhuzYhAy/+Gwu3ml8HQVywJaV6LrQGW5LTtSbry9zI/XoD7cpKWL7bhEk1kn4jGnhvVC0Gy9PWYXawOjs
                EhIRpkyZcu677767UVf7s17b35cYQICIRkaj0U2sR52ANdktQcLCT+fh+R1PId9fEEP4bkzA7XeMw95U7RlCrBslvjL899G/wNQB56NQLoIEKW7TBwmEZuUArv5wOtqirfBLeYI3OznizyRjcHMSZiUn2KsIJ01G4fW308EHQCd8BUGlE3PH3IUfjLwJMuRk3HjIYHkTmzRp0rlr1qz5VFD7+zzx95YJQAACixcvPps7XeBpSAMAkP0y/vHlCyaY
                AvQIgBjL55wBQjsw0YbjAtqtFs1jYFDRpXRhWGEtbjt6HsaXnY5SX5lt09mLhGJfKQNHhW8AXpn0AT48uAq3bbgGfsqDj3wgkuKCY1qApdyevkupFP26uyrtQJ+CysDtPTqTwRm2uyq45xuP1wnZqzTabg5wezmmbdpGCNaQ+NDeIFMRjHZi4sApWHjiYyj2len7wGW1YkCOKTbi4FiQZNiDoijBE0444bzPP/98q+Dw6xfE31sagAxg4K5dXzxf
                XT3kTGsxyZGo4XgXYodZM9NLO3db22c4Z9kEVAYGQJZlzQQgAhkagGTF3CWykoLEV8g4gwoF7UobJpSfjpuPuhNji49Dua8SKlRbAYpIRKaU5lx39pLg+LVnuiuI4rX9L+GeTT9Gib8MMmRPoBKbtDZDl+TtwfeiwUT9xpPsR+6ZB5Tou/F6hLt8hzsSnLiVwRObwmuYA5ybnzHGoHIV3dEgRhSNwv875a+oyR8BJrxDGxGTV8NkimU03J1EjPZi
                NiRo4ujq7Ppq9OjRlzY3N+/SiT/an4i/txhAAECtqqqbmd5OOW7wLS6Wsybpf/Xx7fjbjmdR4A9AkiTzhxxwYiRJtmADB0OUR9ERbcfZQ2Zg9sibcVTRsSj1l0FlakK1NR3tWSIJQbULLzc8j4Vb/gdl/nLI5NN9BIgbhkvkeHI7bqtiTAZUz3Eo/vfjL0zC2IOHxmdqWB6deN1+G624g0oXagLD8Yfxz2BMyTirNZce4nRqGGJTTxKEDBc0MJuA
                Ig731h32I7t3735v1KhRNwHYAwvRp18Rf28wAAJQXldXN2f69Om/y0T6r8/nw/i/DUeQd8Iv+0GSZDoBDSAQkowcMQZGHBEWQYSFcMmwq3DpsO/jmNITEZADUFj2qi8lkhBi3Xh5z/P4P/XzEJAL4Zf8kCBZmXUOcyBmm7l2kaEY4BFyqPgJuw672fCUiJjj1+WLWU9c1OqF5B6x6s8OpsKFrrswIbqhY/KrTEVntB3HlJ2IX417AOPKTvR+l72M
                gkxE+Oijj/56+umn/4aI9veVst6+wgB8AAbs3r37hcGDB0/OxAXr2zZjSt2JqAyUQ5ZlzQTQNQBDbebE0K2G4Jd9+F7tbEyrvhQnlk+ADBkKP7TvRiIJKlewvPEV/K7+V2iPtmlRA0iOiIWocqbmNCQdKDVuUwwib0rwYBh2KG1KyqPv5rRzYyZGbgJ38fYzMNO51x49iOnVM3Hdkbfj6NJjkR6mRIZsW0nC3196af7MmTOfJaIDnPM+l9t/qBlA
                AMAIRVE+c/ZI42lNjvCT967HSzue09R/WVf9JZ3olW5UBQbie6Nm45whM3BC5QRwBqhc6YMLTZAlGe+3rMKzux7Ge01vodhXBp/ki4kc2JkCJRHy8y5xJkoBASBZFBK4eP1F7L4EzMGsq3Ck7xrSvlvpQpGvGLNHzcVFNVdgQN7ArGpvroxckrBgwYIfzps3bwU0CO+sNvDoD1EAAhB49dVXL3aSfLqGgOyT8frOfwEMUNQomMrQzUI4snw0Zh55
                NaYNvRhjK44HV7UEkEMpHRJr2RwKU3BK+UScMX4y9ocaUNfwPBZ/8TRao60olIsgk6RjHOjJL5wAMCHH36xzFv4WVG/uobvbHInc0xFmfezBspkH8Xu8aLsdTwBntl3BAXCm516oEXQpnThr0Pm4YsS1mDhgCpjKwMDiEr+ncMkggGEwGNw3ZcqUK9etW1cPLczXZ+r5+5IG4AMwoKGh4aWBAweeEe+dxLadFHu0W5/Ut27BCc8dj0AeMH7wOHzn
                yCtwyajvYUTpkdrmEEI+Ri0BDAgopxc4jZ1BicnFEzMjORBOCbJPwsct7+MfexZj+b5/IcSCKJCLIEuSBXcOt4YmDqnPCa7tEbxmI7j9bYDH4h+UAtlxjT+QWBhkGfUOSW/l6QeVLhxfNh4zamZiRs3lKJFLU5L27k8nQPYkemnG7nMJA0iShM+3fb5szNgxP4aG4deBfhbmyyYDCAAYrijKFnufNhH3iZsFQZy7kBcJ0M9E+P1Hvwckjtnj5mBA
                4QCoiuC5N0Ny3KxxESGmLAcULM9YTABc/BJPfqcZjEYAoIALI3BUkwiY9FYxlPEtn+QDJOCDplV4reHveL95FfaHGjTnoezXy3IlDdZMYAp2J6BusxsIyTEUr2kXrlGEOM4/Z5We7S9u+dhjynHBhR57WvgurIbAOMOJ5d/AlCPOw8VDr0SZv1yLyggQXFYjTy3H3oazRFx4nSIkiFgbYv2fC3vPAn7hFuy4w7kKzgGJsPS1pb+ZMWPG09DSejv7
                s7OvtxkAEVH50qVLbzr77LPnG0k53sqwB0qc45AsyRnoxyZW4aXjHvbOU++1vnqkRTgagrvxz4YXsLrpHWzt3IygEkRALoAs+czUY7LV7SdwAPZg0iZTjSP8mA6SYNZSMIYICyPKIqgJjMDx5Sdj6hHTcfbgGQDg+W45T6GbkfN71LO9QiShs7Nzz0UXXTTn7bff3qyr/Ieka09/YgA+AAP379//z6qqqm+kv8OQG67eZxkgYFv7Z3ht79+xsfUj
                7Al+if3hBvgkH3ySHz7ym4QuOXokkCs2QHpM1LTdbaE7BpUxqExBhIeRLxVgWGEtRhcfgzOPmIYzB02DT/KBM57R7rqZZ7yELVu2vDxu3Lg7JElqZYx97VT+3mIAAQA1iqJsy5FrFhgCyYY2j/ea38Ka5v/gk7aP0RI+gFalFe3Rg3rzVBlEMmSSIEEWAEIpJeLnuuRnULVMPKhQmYICOYByfyXK8ypRXTAc36iciMlHnI3qwDDNJ8BYj2sEskX4
                4XC47f7777/1vvvueweal7/766jyu0nuTKj/BW+8/saVTpCG3OidoXLVjD6fVjEZp1VMBoHM3AgA2N+9B5vaN+CLzu3Y1bUdu7t3olvtRoSFoPAoFKaYhVC6tW4aZjL54CMZPvIjT8qDX8pHRV4VhhfWYmTRURhTehzGlByHPDlf1/31ORnzU/tXaHznzp2vjx49eq4sy+0A2tBPKvn6igbgBzCgqalpaXl5+Yn97eH5YTRXs2Q52da+RtiPM7B4
                jcbS7j126N6ALvVbbrv9tuufePyJNYKtH8VhNDLBAAoBVGdc/e/J3nBg4fNM3jjOx/G+6V5Lo3ujXcJUxFMLKab8JIkmy722CU/yvo5iG/MD3RPvCMXZntZlsSiZuycE7zO7Dapr1nz0zBlnnLFQkqR2xli7buszHGbDlwEyLVixYsUs0oE6zQo5IdTnHoq1UF5co3Cu4TUSW0J45BLACr2ZFXzJk6RrLyiTIIU8AzjDfVYVoQ2fXvh/bK8p7nHc
                SvwR0W8AyxPvhKITiwCIu/QvFNZY7MdhfWY9lViJ6WybyF37oVlFNkaY1xaGjVldJ0MxJqZ/ydbqy8D7FwBLxfI+IcRLIuoZCVELgob9B46DBw9uqqmpmROJRBoAtDLGQoeDre+pFWaAgQQmTJhwGedMb81EMXLADTvfSkIhe7W8CEFtlvbCAgo1I1pCT0C9oaftfKEkOAYV2ES/5bHluub/BXhsTkaei9BkVJ+3Cf8tFLxwoRxZ33xkzkNHLbKm
                KyB3O4CxBfBQ4nb1VXx2ElpXGSi8MWAonOw3NODADbBtc0KitHQ2FeH26kurFYsV1hU6dpjw3WTBo5vLwq33akCJW8lN+hqTntwlfM8keuO7XLgPSM8Nsd6dMc+oEm276qqrLh44cOCMSCSyDRpOf9fhTPyZYAB5AApLSkqOsWPTCxtVrM8n2DcsmViu1mcQEfu4bSOa257I3hNAYC9ObHmTAQn48ty8pJ0hmW3Cze4yXNlaX7/sjDNOv8jn832r
                sXH/f0z5TLHApiQyLgj3cKdqxPQFgPBMAoMUD7v0pbIzV3KrKSDhsg6cQtf1s6ZgMi649961sVWB14jy3bONmbgcjsxGL8R1W/cAcpxIlupoJBJxzpUHH3zwloKCgtNeeOGFdwHs1R19X+vwXjZMAAKQv2LFilmSJFHq3v9EgJmJ3RMpRbMo0d20o4yx6Jo1a/529dVX/++OHTv267HgLgBqdXX1d4cPHz5w48aNz5eUlIw73FIX0mkxTtleIIHp
                LVq06O5Zs2bVcc6Nxhxh9PPqvb7kBPQDGNTW1vZmcXHxUf12AYgQjUa731j+xhNzb5n7j4aGhgORSKQNWrVXSJcUqu4gkgHkAygZP3589fLly/9UUVFxci702bfe56JFi+6+4YYbXuno6DgADawjfLir+r3BAIqgef8/IyK5X9k9koRgMNjywgsvPLhw4cJVW7du3c8573Ahei/KNhhB8cSJE4cuWbLkt9XV1Wf3DADV04196HcI7x+E//jjj99+
                9913r2xubj4gSPwc4fcCAyAAlStWrLjtrLPOurs/SEBJktDS0vLFE0888cfFixev27Bhwz5oBR4G0UcTEH08RlB42mmnVT/22GPXnXTSSbf0nBEkS5d9lTqzMy8iQnd3d9PPf/7zW5566qkN3d3dRtFOJEf4vcsA/AAGdXR0/LuwsLC2J9vAHg5OBznYe3MQEfbs2bPu4YcffnTZsmVb1q9fv1e354P6JkmH6F35CxHlc84DxxxzzIC77777W5dd
                etnv/Pn+Us54couR8mKlQWfx1jfOZ64Iwl4x95jEC/ciae/S8MSPJEkS6rfUv/rzu37+UF1d3ee6tO/S32eO8LPAAIoADFUUZZNN/Xe8PaP4hDtqwuGyHcSYt9W3LWEptyNOrRH91q1b33r66aefq6ur21JfX79fJ/huXdKrGSJ6r/X0AygAUHLHHXeMve66664bPXr05VbxjB39wATX5Pa8CFtKg2N94q+D3V8fs+om5fHYC3hghZtBRrEMNyYn
                wCjbdZaB22P1diZitNOy40GQcJbBbCSSEAp1t7744t8XPPDAA++sX79+DxF1cc6N7D2WI+esmVtUtWLFivmMMc5UlauqyhnTfhs/TP9RVcYZUzlTGVcZ40xlnDH9mP59pqpcNb+vnaeqTPu/cF3zfsLnnHOuqipfv379y3feeec1ejViLYBBAEp1FV1Gdh32BC3CUgig6qijjhr7l7/8ZXZTU9NHnHNtHYzn19fG+s30tVLNH6YyfR2FtTTXh5k/
                TFw31XGefi4TryneS3wPxnHbOcz8TBXnoxrXNM53vC+mWj+2z7W/tTmrtmsZ+4ZzzhVFUVevXv3k9ddffwGAkQAG6gLIj1z96CEZfgDDurq6vrI2hPXCzd/M2LDCj2r/v7VJYn/ifcY555FIJPTee+/95c4775wF4AQAIwAcAaAEWn5CX3FMSjoTKgUwYPr06eNfeeWV21paWj7h+jCfmXk/c2//mIw62/dWY99tNBpVNmxY/9z8+fMvB3A0gEFE
                VKavo5QjwUNrAhQCGKGq6kYi8mVtokTo6upqWbt27Ut1dXVv/uEPf9gAoIOIQroaaDh++rIqKOsMNB+A/9xzzx128803T5wwYcLFgwcP/rYkSf2zmrIHCRFGslJnZ+feTz755OWVK1e+PW/evHW6My8kOGgZcok7fYJhVC1fvvw+m/ToBclgjJaWli9Wrlz58Jw5cy7RpcEwIqoS1MD+KhFk3VdQCqAKwIiHHnroknXr1v3x4MGDm5zawdflxxjh
                cLhr+/bty15++eU7ZsyYMRnAMN1sK9PXJdtmW04DSFL9HxIMBtcUFBQc0RtSHgAOHDiwZd26da//8Y9/XLZ06dLPdSkghuuUr5k0kPQNnyeYL+VPPvnkKaeccsrpQ4YMOaWiouIkv98fANBvtASxxqKjo2P3vn371m7fvv2jRYsWffDnP/95m/4+FWjxejHhKifp+ygDKAQwUlXVDZlK/jE2yd69ezesW7fujZtuuumVL774okEgenFz8MPknUgA
                ZCLyc84NhpB3ySWX1F5zzTXjR40adXxVVdUxpaWlRwcCgUE2kM9DwBzE+0ej0VBnZ+fOgwcPbv/qq682ffDBB+vuuOOOT6B3sTcJAAACeUlEQVT1zlN1Bh4RGHmO4PsJAyAAlcuWLbv1nHPOmdfTDcMYQ0NDw5o1H3647JJLL/0HLLz1oCAZ1NzmsGkIPl0L8wnHCq666srhF1/8nWNHjhx5dGVl5fBAIHBEIBA4Ii8vr9Ln85X5/f78TEyCMYZo
                NNoRiUQOhsPh5lAodKCtra2hoaFh5/r16+vvueee+mAw2CLY7Ir+d1R4n7lwXT9lAH4ANaFQaG1eXl5lOkQfjUbD+/bt+/jNN9/85zXXXPOKQOxdwkbJEX1y7834kYUfn/5bEjQJCYBcVlZWOW3atIqxY8eWDx40uGTAwAGl+fn5+UQkFRQU5HPOiYh4MBjsZoypHR0dwZaWls4vv/yyfdWqVc1r1qxp0rUxJvxAf18GcavC/3mO2L9eDKAIwChV
                VdcTkZQs0YdCofbGxsaNS5YsWfzTn/50ha7+GYk5EeQ8vL3FHOBgBIDlWCMkBgYz3gcTiNn4mzsIPPfuDoNNNWDp0qX3JuPhDQaDzdu3b1956623zoLmua+FlsBRDCsxJzdyIzf6yfAR0dBIJNLOGOOccRvRM8Z4V1fXgS2fffbKOeecMwPAGGiJOQbR5yGXwJEbudFvR355WdlIplG9kX7Lurq6Dnz88ceLampqztKJfjiAAbq5kCP63MiNr8nI
                q6+vv5WpLNodCu3797///TCAMwCMhZbAUQktRJjLz86N3OhPqn2S57GioqJGSZYG6zY8g+YRDuPrmZiTG7lxWIxUYN7E1EzRI5wbuZEbuZEbuZEbuZEbuZEbuZEbuZEbuZEbuZEbuZEbuZEbuZEbuZEbuZEbuZEbuZEbuZEbuZEbuZEbh2r8f9MLG+nctDnXAAAAAElFTkSuQmCC"""


    @classmethod
    def Instance(cls):
        if cls.INSTANCE is None:
             cls.INSTANCE = LocalInstaller()

        return cls.INSTANCE

    def __init__(self):
        if self.INSTANCE is not None:
            raise ValueError("An instantiation already exists!")

        self.CUR_SCRIPT_PATH   = os.path.realpath(__file__)
        self.WRAPPER_DIR_PATH  = os.path.expanduser("~/.whatsappwrapper-indicator") + "/"
        self.SCRIPT_FILE_PATH  = self.WRAPPER_DIR_PATH + os.path.basename(__file__)
        self.ICON_FILE_PATH    = self.WRAPPER_DIR_PATH + "whatsapp.png"
        self.DESKTOP_FILE_PATH = os.path.expanduser("~/.local/share/applications/whatsapp.desktop")
        self.CHROME_DATA_DIR   = self.WRAPPER_DIR_PATH + "chrome-profile/"
        self.CHROME_FIRST_RUN  = self.CHROME_DATA_DIR + "First Run"

        self.DESKTOP_FILE_CONTENT = "[Desktop Entry]\n" + \
                                    "Version=1.0\n" + \
                                    "Name=WhatsApp Web\n" + \
                                    "Comment=Chat on WhatsApp from the Web\n" + \
                                    "Exec=" + self.SCRIPT_FILE_PATH + "\n" + \
                                    "Terminal=false\n" + \
                                    "Icon=" + self.ICON_FILE_PATH + "\n" + \
                                    "Type=Application\n" + \
                                    "Categories=Network;WebBrowser;\n" + \
                                    "MimeType=text/html;text/xml;application/xhtml_xml;image/webp;x-scheme-handler/http;x-scheme-handler/https;x-scheme-handler/ftp;\n" + \
                                    "StartupWMClass=whatsapp-web-app"


    @staticmethod
    def sha256sum_file(file_name, block_size=65536):
        sha256_hasher = hashlib.sha256()

        with open(file_name, mode="rb") as f_handle:
            buf = [None]
            while len(buf) > 0:
                buf = f_handle.read(block_size)
                sha256_hasher.update(buf)

        return sha256_hasher.hexdigest()


    @staticmethod
    def sha256sum_string(data, decode_type=None):
        if decode_type is None:
            digest = hashlib.sha256(data).hexdigest()
        else:
            digest = hashlib.sha256(data.decode(decode_type)).hexdigest()

        return digest


    def compare_hash(self, file_name, data, decode_type=None):
        if not os.path.exists(file_name):
            return False

        return self.sha256sum_file(file_name) == self.sha256sum_string(data, decode_type)


    def compare_file_hash(self, file_name_1, file_name_2):
        if not (os.path.exists(file_name_1) and os.path.exists(file_name_2)):
            return False

        if file_name_1 == file_name_2:
            return True

        return self.sha256sum_file(file_name_1) == self.sha256sum_file(file_name_2)


    def write_file(self, file_name, file_data, decode_type=None):
        file_written = False

        if not os.path.exists(os.path.dirname(file_name)):
            os.makedirs(os.path.dirname(file_name))

        if not os.path.exists(file_name) or not self.compare_hash(file_name, file_data, decode_type):
            with open(file_name, mode="wb") as f_handle:
                if decode_type is None:
                    f_handle.write(file_data)
                else:
                    f_handle.write(file_data.decode(decode_type))

                f_handle.flush()

            file_written = True

        return file_written


    def install(self):
        need_restart = False

        need_restart |= self.write_file(self.ICON_FILE_PATH, self.ICON_DATA, decode_type='base64')
        need_restart |= self.write_file(self.DESKTOP_FILE_PATH, self.DESKTOP_FILE_CONTENT)
        need_restart |= self.write_file(self.CHROME_FIRST_RUN, '')


        if not self.compare_file_hash(self.CUR_SCRIPT_PATH, self.SCRIPT_FILE_PATH):
            shutil.copyfile(self.CUR_SCRIPT_PATH, self.SCRIPT_FILE_PATH)
            need_restart = True

        if need_restart:
            raise LocalInstaller.RestartNeeded()



class UnityNotRunning(Exception):

    def __init__(self):
        super(UnityNotRunning, self).__init__()



class UnityHelper(object):

    INSTANCE = None


    def __init__(self):
        if self.INSTANCE is not None:
            raise ValueError("An instantiation already exists!")

        self.unity_running = False


    @classmethod
    def Instance(cls):
        if cls.INSTANCE is None:
             cls.INSTANCE = UnityHelper()

        return cls.INSTANCE


    def check_unity(self):
        if not self.unity_running:
            try:
                ins = Unity.Inspector.get_default()
                self.unity_running = ins.get_property('unity-running')
            except:
                pass

        if not self.unity_running:
            raise UnityNotRunning()

        return True



class WALauncher(threading.Thread):

    def __init__(self, chrome_path="/usr/bin/google-chrome-stable"):
        super(WALauncher, self).__init__()
        self.chrome_path = chrome_path


    def run(self):
        sp_whatsapp = subprocess.Popen([self.chrome_path,
                                        "--app=https://web.whatsapp.com",
                                        "--user-data-dir=" + LocalInstaller.Instance().CHROME_DATA_DIR,
                                        "--no-default-browser-check"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        sp_whatsapp.wait()

        loop.quit()



class CompizNotFound(Exception):

    def __init__(self):
        super(CompizNotFound, self).__init__()



class WAWindow(XWindow):

    class CompizNotFound(Exception):
        def __init__(self):
            super(WAWindow.CompizNotFound, self).__init__()


    def __init__(self):
        self.whatsapp_window = None

        try:
            self.w_compiz = XWindow(XTools.Instance().get_window_by_class_name('compiz'))
        except XWindow.WindowIsNone:
            raise WAWindow.CompizNotFound()

        XTools.Instance().get_root().change_attributes(event_mask=X.SubstructureNotifyMask)
        self.w_compiz.window.change_attributes(event_mask=X.SubstructureNotifyMask)

        self.thread = threading.Thread(target=self.find_whatsapp)
        self.thread.start()

        self.wa_launcher = WALauncher()
        self.wa_launcher.start()

        self.thread.join()

        super(WAWindow, self).__init__(self.whatsapp_window)

        self.set_app_class('whatsapp-web-app')
        self.window.change_attributes(event_mask=X.PropertyChangeMask)


    def find_whatsapp(self):
        while self.whatsapp_window is None:
            if self.w_compiz.next_event():
                self.whatsapp_window = XTools.Instance().get_client_by_class_name('whatsapp')



class WACountUpdater(threading.Thread):

    def __init__(self, wa_window):
        super(WACountUpdater, self).__init__()
        self.wa_window = wa_window
        self.u_launcher = Unity.LauncherEntry.get_for_desktop_id ("whatsapp.desktop")
        self.re_w = re.compile('^\((\d+)\)(:?.+)?$')
        self.setDaemon(True)
        self.start()


    def update_count(self, count):
        bool_enable = (count is not 0)

        self.u_launcher.set_property("count-visible", bool_enable)
        self.u_launcher.set_property("count", count)
        self.u_launcher.set_property("urgent", bool_enable)


    def parse_title(self):
        try:    notif_count = int(self.re_w.match(self.wa_window.get_title()).group(1))
        except: notif_count = 0

        return notif_count


    def run(self):
        while True:
            self.wa_window.next_event(instance=PropertyNotify, atom=_NET_WM_NAME)
            GObject.idle_add(self.update_count, self.parse_title())



if __name__ == "__main__":
    try:
        UnityHelper.Instance().check_unity()

        LocalInstaller().Instance().install()

        loop = GObject.MainLoop()

        t_wacu = WACountUpdater(WAWindow())

        loop.run()
    except UnityNotRunning:
        print "Unity not found!"
        sys.exit(-1)
    except CompizNotFound:
        print "Compiz not found!"
        sys.exit(-1)
    except LocalInstaller.RestartNeeded:
        os.chmod(LocalInstaller.Instance().SCRIPT_FILE_PATH, 0755)
        os.chmod(LocalInstaller.Instance().DESKTOP_FILE_PATH, 0755)
        subprocess.call([LocalInstaller.Instance().SCRIPT_FILE_PATH])
