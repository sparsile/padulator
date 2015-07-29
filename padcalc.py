#!/usr/local/bin/python3
import sys
import os
import time
import json
import numpy as np
import functools
import requests
from cachecontrol import CacheControl
import pickle as cPickle
from enum import Enum
import itertools
import decimal
import flowlayout

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit, QComboBox,
        QHBoxLayout,QVBoxLayout,QGridLayout,QAbstractButton,QSizePolicy,QPushButton,
        QCheckBox,QToolButton,QBoxLayout,QMenu,QAction,QFrame)
from PyQt5.QtGui import (QPixmap, QIcon, QPainter, QColor, QPen, QFont,
        QPainterPath, QBrush,QDoubleValidator, QFontMetrics)
from PyQt5.QtCore import QSize, pyqtSignal
from urllib.parse import urljoin


API_ENDPOINT = 'https://www.padherder.com/user-api'
URL_MONSTER_DATA = 'https://www.padherder.com/api/monsters/'
URL_LEADER_DATA = 'https://www.padherder.com/api/leader_skills/'

URL_USER_DETAILS = '%s/%%s/%%s/' % (API_ENDPOINT)
PRONG_ID = 27

class Orb(Enum):
    Null = 0
    R = 1
    B = 2
    G = 3
    L = 4
    D = 5
    H = 6 # heart
    J = 7 # jammer
    P = 8 # poison
    def __str__(self):
        return str(self.name)

class Type(Enum):
    Null = None
    Evo = 0
    Balanced = 1
    Physical = 2
    Healer = 3
    Dragon = 4
    God = 5
    Attacker = 6
    Devil = 7
    Awoken = 12
    Protected = 13
    Enhance = 14
    def __str__(self):
        return str(self.name)

TYPES = [Type.Evo, Type.Balanced, Type.Physical, Type.Healer, Type.Dragon, 
        Type.God, Type.Attacker, Type.Devil, Type.Enhance]
ORBS = [Orb.R, Orb.G, Orb.B, Orb.L, Orb.D,Orb.H]
COLORS = {
        Orb.R: Qt.red,
        Orb.G: Qt.green,
        Orb.B: QColor(137,207,240),
        Orb.L: Qt.yellow,
        Orb.D: Qt.magenta
        }
ROWS = {
        Orb.R: 22,
        Orb.B: 23,
        Orb.G: 24,
        Orb.L: 25,
        Orb.D: 26,
        Orb.H: -1
        }
ENHANCE = {
        Orb.R:14,
        Orb.G:16,
        Orb.B:15,
        Orb.L:17,
        Orb.D:18,
        Orb.H: -1
        }
STAT_AWAKENINGS = {
        'atk': 2,
        'hp': 1,
        'rcv': 3
        }
STAT_AWK_BONUS = {
        'atk': 100,
        'rcv': 50,
        'hp': 200
        }
EAWK_BONUS = 0.05;
ENH_BONUS = 0.06;
PRONG_MULT = 1.5;
ROW_MULT = 0.1;


headers = {
    'accept': 'application/json',
    'user-agent': 'padulator'
}
global session
session = requests.Session()
session.headers = headers
# Limit the session to a single concurrent connection
session.mount('http://', requests.adapters.HTTPAdapter(pool_connections=1, pool_maxsize=1))
session.mount('https://', requests.adapters.HTTPAdapter(pool_connections=1, pool_maxsize=1))
session = CacheControl(session)

def we_are_frozen():
    """Returns whether we are frozen via py2exe.
    This will affect how we find out where we are located."""

    return hasattr(sys, "frozen")

def module_path():
    """ This will get us the program's directory,
    even if we are frozen using py2exe"""

    if we_are_frozen():
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(sys.executable))),'Resources')

    return os.path.dirname(os.path.abspath(__file__))

class CardIcon(QWidget):
    def __init__(self):
        super().__init__()
        self.pixmap = QPixmap()
        self.setMinimumSize(self.sizeHint())
        self.setSizePolicy(QSizePolicy())
        self.card = None
        self.main_attack = 0
        self.sub_attack = 0

    def sizeHint(self):
        return QSize(50,50)

    def paintEvent(self,event):
        global monster_data
        global dmg
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.drawPixmap(event.rect(),self.pixmap)

        if self.card is not None and self.card.ID is not 0:
            card = self.card
            # Draw card level at the bottom centered
            pen = QPen()
            if np.floor(card.lv) == monster_data[card.ID]['max_level']:
                lvstr = 'Lv.Max'
                brush = QBrush(QColor(252,232,131))
            else:
                lvstr = 'Lv.%d' % np.floor(card.lv)
                brush = QBrush(Qt.white)

            path = QPainterPath()
            pen.setWidth(0);
            pen.setBrush(Qt.black)

            font = QFont()
            font.setPointSize(11)
            font.setWeight(QFont.Black)
            
            path.addText(event.rect().x(),event.rect().y()+48,font,lvstr)

            rect = path.boundingRect()
            target = (event.rect().x()+event.rect().width())/2

            # center the rect in event.rect()
            path.translate(target-rect.center().x(), 0)

            painter.setPen(pen)
            painter.setBrush(QBrush(Qt.black))
            painter.drawPath(path.translated(.5,.5))

            painter.setPen(pen)
            painter.setBrush(brush)

            painter.drawPath(path)

            # Draw +eggs at the top right
            eggs = card.plus_atk+card.plus_hp+card.plus_rcv
            if eggs > 0:
                eggstr = '+%d' % eggs
                pen.setBrush(Qt.yellow)
                brush = QBrush(Qt.yellow)

                path = QPainterPath()
                pen.setWidth(0)
                pen.setBrush(Qt.black)
                font = QFont()
                font.setPointSize(11)
                font.setWeight(QFont.Black)
                path.addText(event.rect().x(),event.rect().y()+12,font,eggstr)

                path.translate(50-path.boundingRect().right()-3,0)
                #painter.setFont(font)
                painter.setPen(pen)
                painter.setBrush(QBrush(Qt.black))
                painter.drawPath(path.translated(.5,.5))

                painter.setPen(pen)
                painter.setBrush(brush)
                painter.drawPath(path)
                #painter.drawText(event.rect().adjusted(0,0,0,0),Qt.AlignRight, eggstr)

            # Draw awakenings at the top left in a green circle
            if card.current_awakening > 0:
                path = QPainterPath()
                rect = QRectF(event.rect()).adjusted(4,4,-36,-36)
                path.addEllipse(rect)
                painter.setBrush(QBrush(QColor(34,139,34)))
                pen.setBrush(Qt.white)
                pen.setWidth(1)
                painter.setPen(pen)
                painter.drawPath(path)

                path = QPainterPath()
                font.setPointSize(9)
                awkstr = ('%d' % card.current_awakening if
                        card.current_awakening < card.max_awakening else
                        '★')
                path.addText(rect.x(),rect.bottom(),font,awkstr)
                
                br = path.boundingRect()
                path.translate(rect.center().x()-br.center().x(),
                        rect.center().y()-br.center().y())

                pen.setBrush(QColor(0,0,0,0))
                pen.setWidth(0)
                painter.setPen(pen)
                painter.setBrush(QBrush(Qt.yellow))
                painter.drawPath(path)

            # Draw main attack damage
            #print(self.main_attack)
            if self.main_attack > 0:
                matkstr = '%d' % self.main_attack
                painter.setBrush(QBrush(COLORS[self.card.element[0]]))
                path = QPainterPath()
                font = QFont()
                font.setFamily('Helvetica')
                font.setWeight(QFont.Black)
                #font.setStretch(25)
                font.setPointSize(13)
                path.addText(rect.x(),rect.bottom(),font,matkstr)

                rect = QRectF(event.rect())
                br = path.boundingRect()
                path.translate(rect.center().x()-br.center().x(),
                        rect.center().y()-br.bottom()-1)

                # 
                pen.setBrush(Qt.black)
                pen.setWidthF(.75)
                painter.setPen(pen)
                painter.drawPath(path)

            # Draw sub attack damage
            #print(self.main_attack)
            if self.sub_attack > 0:
                satkstr = '%d' % self.sub_attack
                painter.setBrush(QBrush(COLORS[self.card.element[1]]))
                path = QPainterPath()
                font = QFont()
                font.setFamily('Helvetica')
                font.setWeight(QFont.Black)
                #font.setStretch(25)
                font.setPointSize(12)
                path.addText(rect.x(),rect.bottom(),font,satkstr)

                rect = QRectF(event.rect())
                br = path.boundingRect()
                path.translate(rect.center().x()-br.center().x(),
                        rect.center().y()-br.top()+1)

                # 
                pen.setBrush(Qt.black)
                pen.setWidthF(.75)
                painter.setPen(pen)
                painter.drawPath(path)

        
    #@asyncio.coroutine
    def load_icon(self):
        global session
        #sys.stdout.flush()
        pixmap = QPixmap()
        #r = yield from aiohttp.request('get',self.card.url)
        #pix = yield from r.read()
        #pixmap.loadFromData(pix)
        pixmap.loadFromData(session.get(self.card.url).content)
        #pixmap.setDevicePixelRatio(2)
        #self.pixmap = pixmap.scaled(100,100)
        self.pixmap = pixmap
        self.repaint()
    
class AttackValue (object):
    def __init__(self, value=0):
        # round the input
        decimal.getcontext().rounding = decimal.ROUND_HALF_UP
        self.value = int(decimal.Decimal(value).quantize(decimal.Decimal('1.0000')).to_integral())

    def __float__(self): return float(self.value)
    def __int__(self): return int(self.value)
    def __add__(self, other): return AttackValue(self.value+float(other))
    __radd__ = __add__
    def __mul__(self,other): return AttackValue(self.value*float(other))
    __rmul__ = __mul__
    def __sub__(self,other): return AttackValue(self.value-float(other))
    __rsub__ = __sub__
    def __truediv__(self,other): return AttackValue(self.value/float(other))
    def __str__(self): return str(self.value)
    __repr__ = __str__
    def __lt__(self,other): return float(self) < float(other)
    def __le__(self,other): return float(self) <= float(other)
    def __gt__(self,other): return float(self) > float(other)
    def __ge__(self,other): return float(self) >= float(other)
    def __eq__(self,other): return float(self) == float(other)
    def __ne__(self,other): return float(self) != float(other)
    def __round__(self): return self.value

class Card:
    use_max_stats = False

    def level(xp,xpmax):
        return np.power(xp/xpmax,1/2.5)*98+1
    
    def blank_card(self):
        self.lv = 0
        self.ID = 0
        self.atk = 0
        self.hp = 0
        self.rcv = 0
        self.element = (Orb.Null,Orb.Null)
        self.tp = None
        self.tp2 = None
        self.awoken_skills = []
        self.current_skill = 0
        self.name = '?'
        self.url = 'https://www.padherder.com/static/img/monsters/60x60/0.png'
        self.leader_skill = None
        self.plus_atk = 0
        self.plus_hp = 0
        self.plus_rcv = 0
        self.current_awakening = 0
        self.max_awakening = 0
        self.prongs = 0

        return self

    def load_from_card(self,card):
        global monster_data

        if Card.use_max_stats \
                and 'target_evolution' in card \
                and card['target_evolution'] is not None:
            monster = monster_data[card['target_evolution']]
        else:
            monster = monster_data[card['monster']]

        if 'lv' in card:
            self.lv = card['lv']
        else:
            # fix off by one error?
            self.lv = int(Card.level(card['current_xp']+1,monster['xp_curve']))

        if Card.use_max_stats:
            self.lv = monster['max_level']
            current_awakening = len(monster['awoken_skills'])
        else:
            current_awakening = card['current_awakening']


        self.ID = monster['id']

        #print(self.lv)

        scaled_level = 1 if monster['max_level'] == 1 else (self.lv-1)/(monster['max_level']-1)
        #print(scaled_level)

        self.awoken_skills = monster['awoken_skills'][0:current_awakening]

        self.atk = float(round(monster['atk_min']+(monster['atk_max']-monster['atk_min'])
                *scaled_level**monster['atk_scale']
                +card['plus_atk']*5
                +sum(np.array(self.awoken_skills)==STAT_AWAKENINGS['atk'])*STAT_AWK_BONUS['atk']))
        self.hp = round(monster['hp_min']+(monster['hp_max']-monster['hp_min'])
                *scaled_level**monster['hp_scale']
                +card['plus_hp']*10
                +sum(np.array(self.awoken_skills)==STAT_AWAKENINGS['hp'])*STAT_AWK_BONUS['hp'])
        self.rcv = round(monster['rcv_min']+(monster['rcv_max']-monster['rcv_min'])
                *scaled_level**monster['rcv_scale']
                +card['plus_rcv']*3
                +sum(np.array(self.awoken_skills)==STAT_AWAKENINGS['rcv'])*STAT_AWK_BONUS['rcv'])
        self.element = (Orb(monster['element']+1),
                Orb.Null if monster['element2'] == None else Orb(monster['element2']+1))
        #if monster['element2'] == None:
            #self.element2 = Orb.Null
        #else:
            #self.element2 = Orb(monster['element2']+1)
        self.tp = (Type(monster['type']),Type(monster['type2']))
        #self.tp2 = monster['type2']
        self.current_skill = card['current_skill']
        self.name = monster['name']
        self.url = 'http://www.padherder.com'+monster['image60_href']
        self.leader_skill = monster['leader_skill']
        self.plus_atk = card['plus_atk']
        self.plus_hp = card['plus_hp']
        self.plus_rcv = card['plus_rcv']
        self.current_awakening = current_awakening
        self.max_awakening = len(monster['awoken_skills'])

        # set prongs
        self.prongs = sum(np.array(self.awoken_skills)==PRONG_ID)

        return self

    def load_from_id(self,user,mon_id):
        global monster_data
        if mon_id is not None:
            card = user.monsters[mon_id]
            return self.load_from_card(card)
        else:
            return self.blank_card()


class Skill:
    # has:
    #   .scope (set of orbs/types)
    #   .condition (default None)
    #   .multipliers 
    def __init__(self,scope=set(), condition=None, multipliers=[1,1,1]):
        self.scope = scope
        self.condition = condition
        self.multipliers = multipliers

    def multiplier(self, card):
        if len(set(card.element+card.tp) & self.scope) > 0:
            return self.multipliers
        else:
            return [1,1,1]
    
    def __str__(self):
        return 'Scope: ' + str(self.scope) + ', Condition: ' + str(self.condition) \
                +', Multipliers: ' + str(self.multipliers)

class popupButton(QPushButton):
    stateChanged = pyqtSignal()
    def __init__(self, labels=[]):
        super().__init__()
        menu = QMenu(self)
        def buttonFuncMaker(lab):
            def buttonFunc():
                self.setText(lab)
                self.stateChanged.emit()
            return buttonFunc

        for t in labels:
            action = menu.addAction(t)
            action.triggered.connect(buttonFuncMaker(t))
        self.setSizePolicy(QSizePolicy())
        self.setMenu(menu)
        self.setFlat(True)
        self.setStyleSheet('''
            QPushButton {
                border-width: 1px;
                border-style: solid;
                border-radius: 7px;
                border-color: gray;
                padding: 1px 3px 1px 3px;
            }
            QPushButton:pressed {
                background-color: gray;
            }
            QPushButton::menu-indicator{
                image: url(none.jpg);
                width: 0px;
            }
        ''')

class tightLineEdit(QLineEdit):
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy())
        v = QDoubleValidator(0,99,3,self)
        v.setNotation(QDoubleValidator.StandardNotation)
        self.setValidator(v)
        self.textChanged[str].connect(self.updateGeometry)
        self.setFrame(False)
        self.setAttribute(Qt.WA_MacShowFocusRect, 0);
        self.editingFinished.connect(self.clearFocus)
        self.setContextMenuPolicy(Qt.NoContextMenu)
        self.setReadOnly(True)
        self.setStyleSheet('''
            QLineEdit {
                border-width: 1px;
                border-style: solid;
                border-radius: 7px;
                border-color: gray;
                padding: 0px 1px 0px 1px;
                background: transparent;
            }
            QLineEdit::focus {
                background: gray;
            }
        ''')
        
    def mousePressEvent(self,e):
        super().mousePressEvent(e)
        self.clear()

    def keyPressEvent(self,e):
        self.setReadOnly(False)
        super().keyPressEvent(e)
        self.setReadOnly(True)

    def sizeHint(self):
        fm = QFontMetrics(self.font())
        minWidth = fm.width(self.text())+8
        supersize = super().sizeHint()
        supersize.setWidth(minWidth)
        return supersize

    #def minimumSizeHint(self):
        #return self.sizeHint()

class SkillViewController(QWidget):
    skillsChanged = pyqtSignal()
    stats = ['hp','atk','rcv']
    def __init__(self, skill=Skill()):
        super().__init__()
        self.skill = skill

        # multiplier
        self.mcontrols = []

        self.layout = flowlayout.FlowLayout(self)
        self.layout.setSpacing(1)
        self.layout.setContentsMargins(0,0,0,0)
        icons = ORBS[:-1] + TYPES
        n = 0
        
        mult = self.skill.multipliers
        if mult[0] != 1:
            wid = self.addMultiplierController()
            wid.control.setText(str(mult[0]))
            wid.label.setText('HP')
        if mult[1] != 1:
            wid = self.addMultiplierController()
            wid.control.setText(str(mult[1]))
            wid.label.setText('ATK')
        if mult[2] != 1:
            wid = self.addMultiplierController()
            wid.control.setText(str(mult[2]))
            wid.label.setText('RCV')

        plusbutton = QPushButton()
        plusbutton.setText('+')
        plusbutton.setFlat(True)
        plusbutton.setSizePolicy(QSizePolicy())
        plusbutton.setStyleSheet('''
            QPushButton {
                border-width: 1px;
                border-style: solid;
                border-radius: 7px;
                border-color: gray;
                padding: 1px 3px 1px 3px;
            }
            QPushButton:pressed {
                background-color: gray;
            }
            QPushButton::menu-indicator{
                image: url(none.jpg);
                width: 0px;
        ''')
        plusbutton.clicked.connect(self.addMultiplierController)
        self.layout.addWidget(plusbutton)
        # add a button that adds more buttons

    def updateMultipliers(self):
        self.skill.multipliers = [1,1,1]
        for mcontrol in self.mcontrols:
            label = mcontrol.label
            control = mcontrol.control
            if label.text() == 'ATK':
                self.skill.multipliers[1] = float(control.text())
                self.skillsChanged.emit()
            elif label.text() == 'HP':
                self.skill.multipliers[0] = float(control.text())
                self.skillsChanged.emit()
            elif label.text() == 'RCV':
                self.skill.multipliers[2] = float(control.text())
                self.skillsChanged.emit()
        pass

    def addMultiplierController(self):
        wid = QWidget()
        wid.setSizePolicy(QSizePolicy())
        layout = QHBoxLayout(wid)
        layout.setSpacing(0)
        layout.setContentsMargins(0,0,0,0)

        statcontrol = tightLineEdit()
        statcontrol.textEdited[str].connect(self.updateMultipliers)
        wid.control = statcontrol

        timeslabel = QLabel('\u00d7')
        timeslabel.setMargin(0)
        timeslabel.setIndent(0)
        timeslabel.setAlignment(Qt.AlignCenter)
        timeslabel.setContentsMargins(0,0,0,0)

        label = popupButton(['HP','ATK','RCV'])
        label.stateChanged.connect(self.updateMultipliers)
        wid.label = label

        layout.addWidget(statcontrol)
        layout.addWidget(timeslabel)
        layout.addWidget(label)

        self.layout.insertWidget(len(self.mcontrols),wid)
        self.mcontrols.append(wid)
        return wid

    def addStatControl(self,i,label=None):
        statbox = QHBoxLayout()
        statbox.addSpacing(1)
        statbox.setSpacing(0)
        statbox.setAlignment(Qt.AlignCenter)
        statlabel = QLabel(self.stats[i] if label is None else label)
        statlabel.setContentsMargins(0,0,0,0)
        statlabel.setAlignment(Qt.AlignCenter)
        statlabel.setFixedWidth(20)
        statbox.addWidget(statlabel)
        statcontrol = QLineEdit()
        statcontrol.setAlignment(Qt.AlignCenter)
        statcontrol.setFixedWidth(40)
        statcontrol.setText(str(self.skill.multipliers[i]))
        v = QDoubleValidator(0,99,3,statcontrol)
        v.setNotation(QDoubleValidator.StandardNotation)
        #v.setRange(0,100,decimals=3)
        statcontrol.setValidator(v)
        #print(v.top())
        def statFuncMaker(j):
            def statFunc(newValue):
                self.skill.multipliers[j] = float(newValue)
                self.skillsChanged.emit()
            return statFunc
        statcontrol.textChanged[str].connect(statFuncMaker(i))
        statbox.addWidget(statcontrol)
        statbox.addSpacing(1)
        self.layout.addLayout(statbox)
        

    def addTypeBar(self,types):
        typebar = QHBoxLayout();
        typebar.addStretch(1)
        for tp in types:
            if isinstance(tp,Type):
                icon = QIcon('types/%s.png' % tp)
            elif isinstance(tp,Orb):
                icon = QIcon('orbs/%s.png' % tp)
            button = QToolButton()
            button.setIcon(icon)
            button.setCheckable(True)
            button.setContentsMargins(0,0,0,0)
            button.setFixedSize(22,22)
            button.setChecked(tp in self.skill.scope)
            def buttonFuncMaker(x):
                def buttonFunc(y):
                    if y:
                        self.skill.scope.update((x,))
                    else:
                        self.skill.scope.difference_update((x,))
                    self.skillsChanged.emit()
                return buttonFunc
            button.toggled[bool].connect(buttonFuncMaker(tp))
            typebar.addWidget(button)
        typebar.addStretch(1)
        typebar.setSpacing(0)
        typebar.setContentsMargins(0,0,0,0)
        typebar.setAlignment(Qt.AlignCenter)
        self.layout.addLayout(typebar)

class Team:
    def __init__(self,cards=[Card()]*6):
        super().__init__()
        self.set_cards(cards)

    def __getitem__(self,*args):
        return self.cards.__getitem__(*args)

    def set_cards(self, cards):
        if len(cards) != 6:
            raise ValueError('A team must have exactly six cards.')

        self.cards = cards

        # store leader skill data as a list of (multipliers, conditions) pairs.
        # Each bonus effect is evaluated and multiplied to get the
        # overall multiplier for each sub. Eventually, add a feature to
        # append/edit this list.

        self.lskills = []
        for skill in [cards[0].leader_skill,cards[-1].leader_skill]:
            if skill is not None and 'data' in leader_data[skill]:
                ls = leader_data[skill]['data']
                scope = set() if len(ls) > 3 else set(ORBS)-{Orb.H}
                for cond in ls[3:]:
                    if cond[0] == 'type':
                        scope |= {Type(i) for i in cond[1:]}
                    elif cond[0] == 'elem':
                        scope |= {Orb(i+1) for i in cond[1:]}
                self.lskills += [Skill(multipliers=ls[:3], scope=scope)]

        # count orb enhances
        self.enhance_awakenings = {}
        for i in ORBS:
            self.enhance_awakenings[i] = 0
            for j in range(6):
                self.enhance_awakenings[i] += sum(np.array(cards[j].awoken_skills)==ENHANCE[i])

        # count row enhances
        self.row_awakenings = {}
        for i in ORBS:
            self.row_awakenings[i] = 0
            for j in range(6):
                self.row_awakenings[i] += sum(np.array(cards[j].awoken_skills)==ROWS[i])

class Board(QWidget):
    valueChanged = pyqtSignal()

    def __init__(self):
        super().__init__()
        global paintOrb
        paintOrb = Orb.R
        self.orbs = np.zeros((5,6),dtype=Orb)
        self.enhanced = np.zeros((5,6),dtype=bool)
        for (x,y) in [(i,j) for i in range(5) for j in range(6)]:
            self.orbs[x,y] = Orb.Null
        grid = QGridLayout(self)
        grid.setSpacing(0)
        grid.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy())
        self.setLayout(grid)
        #self.resize(5*40,6*40)
        self.grid = grid
        for (x,y),v in np.ndenumerate(self.orbs):
            o = OrbButton((x,y),self)
            grid.addWidget(o,x,y)

        self.grid.setContentsMargins(0,0,0,0)
        #self.set_orb((0,range(6)),Orb.G)
        #self.set_orb((1,range(6)),Orb.L)
        #self.set_orb((2,range(6)),Orb.G)
        #self.set_orb((3,range(6)),Orb.L)
        #self.set_orb((4,range(6)),Orb.G)

    def mouseMoveEvent(self,event):
        sz = self.geometry().width()/6
        (i,j) = (np.floor(event.pos().y()/sz),np.floor(event.pos().x()/sz))
        if i in range(5) and j in range(6):
            self.grid.itemAtPosition(i,j).widget().click()

    def set_orb(self,coord,orb=None,enhanced=None):
        global paintOrb
        if orb is None:
            orb = paintOrb
        if enhanced is not None:
            self.enhanced[coord] = enhanced

        self.orbs[coord] = orb

        c1 = ([coord[0]] if type(coord[0]) == int else coord[0])
        c2 = ([coord[1]] if type(coord[1]) == int else coord[1])
        for (i,j) in [(i,j) for i in c1 for j in c2]:
            self.grid.itemAtPosition(i,j).widget().value = orb
        self.repaint()
        self.valueChanged.emit()

    def match(self):
        board = self.orbs

        matches = {o: [] for o in ORBS}
        enhanced = {o: [] for o in ORBS}
        rows = {o: 0 for o in ORBS}

        se_conn = [[0,1,0],[1,1,1],[0,1,0]]
        se_row = np.ones((1,6))
        se_h = np.ones((1,3))
        se_v = np.ones((3,1))

        # Process current board
        newmatches = 1
        while newmatches > 0: 
            newmatches = 0
            for i in ORBS:
                # first get the rows: open using the row strel, then 
                # reconstruct
                #l,n = lab(recon(mopn(board==i,se_row),structure=se_conn,mask=(board==i)),se_conn)
                #rows[i] += n
                
                # now get all matches
                #l,n = lab(np.logical_or(mopn(board==i,se_h),mopn(board==i,se_v)),se_conn)
                l,n = label_components(np.logical_or(morph_open(board==i),morph_open(board.T==i).T))

                # list of lengths of matches
                for j in range(1,n+1):
                    matches[i] += [(l==j).sum()]
                    enhanced[i] += [self.enhanced[l==j].sum()]

                newmatches += n

                # count separate rows
                maybe_rows = [all(row) for row in l>0]
                row_set = set()
                for k in range(5):
                    if maybe_rows[k]:
                        row_set.add(l[k,0])

                rows[i] += len(row_set)


                # Count enhanced orbs in each match

                # Set matched orbs to Null
                board = np.where(l>0,Orb.Null,board)

            # Advance board state
            for (i,j) in [(i,j) for j in range(6) for i in range(5) ]:
                if board[i,j] == Orb.Null:
                    board[range(i+1),j] = np.roll(board[range(i+1),j],1)
                    pass

        return (matches,enhanced,rows)

def label_components(m):
    linked = [{0}]
    label = 0
    b = np.zeros(m.shape,dtype=int)
    for (i,j),v in np.ndenumerate(m):
        if v:
            N = b[i-1,j]
            W = b[i,j-1]
            if N > 0:
                b[i,j] = N
                if W > 0 and N != W:
                    linked[N].add(W)
                    linked[W].add(N)
            elif W > 0:
                b[i,j] = W
            else:
                label += 1
                b[i,j] = label
                linked += [{label}]
        else:
            b[i,j] = 0

    for (i,j),v in np.ndenumerate(b):
        if v > 0 and len(linked[v])> 1:
            b[i,j] = min(linked[v])

    labels = list({min(linked[v]) for v in range(label+1)})
    for i in range(1,len(labels)):
        b[b==labels[i]] = i

    return b,len(labels)-1

def morph_open(m):
    # implement as horizontal row of 3 structuring element
    b = np.zeros(m.shape,dtype=int)
    for (i,j),v in np.ndenumerate(m):
        if i-1 > -1 and i+1 < m.shape[0]:
            b[i,j] = np.min(m[i-1:i+2,j])

    m = b.copy()
    for (i,j),v in np.ndenumerate(m):
        if i-1 > -1 and i+1 < m.shape[0]:
            b[i,j] = np.max(m[i-1:i+2,j])
        elif i+1 < m.shape[0]: # i-1 = -1
            b[i,j] = np.max(m[i:i+2,j])
        elif i-1 > -1:
            b[i,j] = np.max(m[i-1:i+2,j])
    return b

class OrbButton(QAbstractButton):
    def __init__(self,position=None,parent=None,value=0):
        #super(OrbButton,self).__init__(parent)
        super().__init__(parent)
        self.value = Orb.Null if value==0 else value
        self.parent = parent
        if position == None:
            pol = QSizePolicy(QSizePolicy.Maximum,QSizePolicy.Fixed)
            pol.setHeightForWidth(True)
            self.setSizePolicy(pol)
            if self.value == Orb.Null:
                p = self.palette()
                p.setColor(self.backgroundRole(),QColor(205,127,50,254))
                self.setPalette(p)
                self.setAutoFillBackground(True)
        else:
            self.setSizePolicy(QSizePolicy())
            self.position = position
            self.pressed.connect(self.onClick)
            p = self.palette()
            if (position[0]+position[1]) % 2 != 0:
                p.setColor(self.backgroundRole(),QColor(205,127,50,254))
            else:
                p.setColor(self.backgroundRole(),QColor(128,70,27,254))
            self.setPalette(p)
            self.setAutoFillBackground(1)

    def pixmap(self):
        p = QPixmap()
        if self.value != Orb.Null:
            p.load('orbs/%s.png' % str(self.value))
        #p = p.scaled(40,40,1)
        return p

    def heightForWidth(self,width):
        return width

    def onClick(self):
        modifiers = QApplication.keyboardModifiers()
        enh = modifiers==Qt.ShiftModifier
        self.parent.set_orb(self.position,enhanced=enh)

    def paintEvent(self, event):
        # Check whether this orb is enhanced
        if type(self.parent) == Board:
            enh = self.parent.enhanced[self.position]
        else:
            enh = False

        painter = QPainter(self)
        painter.drawPixmap(event.rect().adjusted(2,2,-2,-2), self.pixmap())

        w = event.rect().width()

        if enh:
            path = QPainterPath()

            pen = QPen()
            pen.setWidth(1);
            pen.setBrush(Qt.white)

            brush = QBrush(Qt.yellow)

            font = QFont()
            font.setPointSize(20)
            font.setWeight(QFont.Black)
            
            path.addText(event.rect().x()+w-15,event.rect().y()+w-5,font,'+')

            painter.setPen(pen)
            painter.setBrush(brush)
            painter.setFont(font)

            painter.drawPath(path)

    def sizeHint(self):
        return QSize(50,50)

class User:
    def __init__(self, username):
        global session
        #sys.stdout.flush()

        self.username = username
        url = '%s/%s/%s/' % (API_ENDPOINT,'user',username)
        r = session.get(url)
        if r.status_code != requests.codes.ok:
            return

        self.user_data = r.json()
        self.teams = self.user_data['teams']
        monsters = {}
        for mon in self.user_data['monsters']:
            monsters[mon['id']] = mon
        self.monsters = monsters

def load_data():
    global monster_data
    global leader_data
    global session
    # always start by reading monster data
    # Check for monster cache (8 hours)
    cache_old = time.time() - (8 * 60 * 60)
    monster_path = os.path.join(module_path(), 'monster_data.pickle')
    #print(monster_path)
    leader_path = os.path.join(module_path(), 'leader_data.pickle')
    if (os.path.exists(monster_path)
            and os.path.exists(leader_path)
            and os.stat(monster_path).st_mtime > cache_old
            and os.stat(leader_path).st_mtime > cache_old
            ):
        # Use cached data
        monster_data = cPickle.load(open(monster_path, 'rb'))
        leader_data = cPickle.load(open(leader_path, 'rb'))
    else:
        # Retrieve monster API data
        #sys.stdout.flush()

        r = session.get(URL_MONSTER_DATA)
        if r.status_code != requests.codes.ok:
            return

        # Build monster data map
        monster_data = {}
        for monster in r.json():
            monster_data[monster['id']] = monster

        # Cache it
        cPickle.dump(monster_data, open(monster_path, 'wb'))

        #sys.stdout.flush()

        # Retrieve leader skill API data
        r = session.get(URL_LEADER_DATA)
        if r.status_code != requests.codes.ok:
            return

        # Build leader skill data map
        leader_data = {}
        for skill in r.json():
            leader_data[skill['name']] = skill

        # Cache it
        cPickle.dump(leader_data, open(leader_path, 'wb'))

class PadCalc(QWidget):
    def __init__(self):
        super().__init__()
        load_data()

        card_tags = ['leader','sub1','sub2','sub3','sub4','friend']
        self.cards = { t: CardIcon() for t in card_tags }

        self.vlayout = QVBoxLayout(self)
        self.vlayout.setSpacing(0)
        self.setLayout(self.vlayout)

        self.userbox = QHBoxLayout()
        userfield = QLineEdit()
        userbutton = QPushButton('Load')
        userbutton.clicked.connect(lambda: self.set_user(userfield.text()))
        self.userbox.addWidget(userfield)
        self.userbox.addWidget(userbutton)
        userfield.returnPressed.connect(userbutton.click)
        self.vlayout.addLayout(self.userbox)

        maxcheckbox = QCheckBox('Use maxed stats?')
        maxcheckbox.stateChanged[int].connect(self.setMaxed)
        self.vlayout.addWidget(maxcheckbox)


        self.teamchooser = QComboBox(self)
        self.teamchooser.currentIndexChanged[int].connect(self.set_team)
        self.vlayout.addWidget(self.teamchooser)

        teambox = QHBoxLayout()
        teambox.addStretch(1)
        for card in card_tags:
            teambox.addWidget(self.cards[card])

        teambox.setSpacing(0)
        teambox.addStretch(1)
        teambox.setAlignment(Qt.AlignCenter)
        self.vlayout.addLayout(teambox)

        self.board = Board()
        self.vlayout.addWidget(self.board)
        self.vlayout.itemAt(self.vlayout.indexOf(self.board)).setAlignment(Qt.AlignCenter)

        self.orbchooser = QHBoxLayout()
        b = OrbButton(value = 0)
        b.clicked.connect(functools.partial(self.setPaintOrb,Orb.Null))
        self.orbchooser.addWidget(b)
        for i in ORBS:
            b = OrbButton(value=i)
            #print('Setting click value of button %s to %s' % (id(b),i))
            b.clicked.connect(functools.partial(self.setPaintOrb,i))
            self.orbchooser.addWidget(b)

        self.vlayout.addLayout(self.orbchooser)

        self.damagereadout = QLabel()
        font = QFont()
        font.setPointSize(30)
        self.damagereadout.setAlignment(Qt.AlignCenter)
        self.damagereadout.setFont(font)
        self.vlayout.addWidget(self.damagereadout)
        self.board.valueChanged.connect(self.update_damage)

        labels = ['atk','combos','leaders','enhance','prongs','rows']
        lfont = QFont()
        lfont.setPointSize(9)
        vfont = QFont()
        vfont.setPointSize(12)
        self.details = {key: QVBoxLayout() for key in labels}
        for i in labels:
            label = QLabel(i)
            label.setFont(lfont)
            label.setAlignment(Qt.AlignCenter)
            label.setMargin(0)
            label.setContentsMargins(0,0,0,0)
            label.setIndent(0)
            self.details[i].label = label
            self.details[i].addWidget(self.details[i].label)
            value = QLabel('1')
            value.setFont(vfont)
            value.setAlignment(Qt.AlignCenter)
            value.setMargin(0)
            value.setIndent(0)
            value.setContentsMargins(0,0,0,0)
            self.details[i].value = value
            self.details[i].addWidget(self.details[i].value)
            self.details[i].setContentsMargins(1,1,1,1)

        self.detailreadout = QHBoxLayout()
        for i in labels:
            self.detailreadout.addLayout(self.details[i])
            timeslabel = QLabel('\u00d7')
            timeslabel.setMargin(0)
            timeslabel.setIndent(0)
            timeslabel.setAlignment(Qt.AlignCenter)
            timeslabel.setContentsMargins(0,0,0,0)
            self.detailreadout.addWidget(timeslabel)

        self.detailreadout.takeAt(self.detailreadout.count()-1)
        self.vlayout.addLayout(self.detailreadout)

        self.vlayout.addStretch(1000)
        self.skillbox = QHBoxLayout()
        self.vlayout.addLayout(self.skillbox)
        #self.set_user('korora')

    def setMaxed(self,state):
        Card.use_max_stats = (state == Qt.Checked)
        self.drawui()
        self.update_damage()
        self.set_team(self.teamchooser.currentIndex())

    def setPaintOrb(self,orb):
        global paintOrb
        paintOrb = orb

    def set_user(self,username):
        newuser = User(username)

        if hasattr(self,'user'):
            olduser = self.user.username
        else:
            olduser = ''

        if hasattr(newuser,'teams') and len(newuser.teams) > 0:
            teamchooser = self.teamchooser
            self.user = newuser
            index = teamchooser.currentIndex()
            try:
                teamchooser.currentIndexChanged[int].disconnect()
            except:
                return

            teamchooser.clear()
            for team in self.user.teams:
                teamchooser.addItem('%s' % (team['name']))

            if newuser.username != olduser:
                self.set_team(0)
            else:
                teamchooser.setCurrentIndex(index)
                self.set_team(index)

            teamchooser.currentIndexChanged[int].connect(self.set_team)

    def update_damage(self):
        (match,enhanced,row) = self.board.match()
        nmatch = sum(len(v) for v in match.values())
        nrow = sum(v for v in row.values())
        (dmg, multipliers) = compute_damage((match,enhanced,row),self.team)
        self.damagereadout.setText('{:,}'.format(round(sum([sum(i) for i in dmg.values()]))))
        for i in multipliers:
            if i is not 'atk':
                self.details[i].value.setText('%.2f' % multipliers[i])
            else:
                self.details[i].value.setText('%d' % multipliers[i])

        for card in self.cards.values():
            # add a damage label
            dam = dmg[card.card]
            card.main_attack = dam[0]
            card.sub_attack = dam[1]
            card.repaint()

    def set_team(self,index):
        teamdata = self.user.teams[index]
        team = []
        for i in ['leader','sub1','sub2','sub3','sub4']:
            team += [Card().load_from_id(self.user,teamdata[i])]
        friend = {
                'monster': teamdata['friend_leader'],
                'plus_atk': teamdata['friend_atk'],
                'plus_hp': teamdata['friend_hp'],
                'plus_rcv': teamdata['friend_rcv'],
                'current_awakening': teamdata['friend_awakening'],
                'lv': teamdata['friend_level'],
                'current_skill': teamdata['friend_skill']
                }
        team += [Card().load_from_card(friend)]
        self.team = Team(team)
        #print('|'+self.teamchooser.itemText(index)+'|')
        #print(len(self.teamchooser.itemText(index)))
        self.teamchooser.setMinimumContentsLength(len(self.teamchooser.itemText(index))-3)
        for i in range(self.skillbox.count()):
            w = self.skillbox.takeAt(i)
            w.widget().deleteLater()
            
        #svc = SkillViewController(skill=self.team.lskills[0])
        #svc.skillsChanged.connect(self.update_damage)
        #self.skillbox.addWidget(svc)
        self.drawui()
        self.update_damage()

    def drawui(self):
        self.cards['leader'].card = (self.team.cards[0])
        self.cards['sub1'].card = (self.team.cards[1])
        self.cards['sub2'].card = (self.team.cards[2])
        self.cards['sub3'].card = (self.team.cards[3])
        self.cards['sub4'].card = (self.team.cards[4])
        self.cards['friend'].card = (self.team.cards[5])
        for card in self.cards.values():
            card.load_icon()

def orb_multiplier(norbs):
    return 1+(norbs-3)/4

def enhance_multiplier(nenhanced,nawk):
    # nenhanced: vector of number of enhanced orbs in each match
    # nawk: number of total team enhance awakenings in the color in question
    return (1+ENH_BONUS*nenhanced)*(1+np.where(nenhanced>0,nawk*EAWK_BONUS,0))

def sub_dmg(sub):
    atk = sub.atk
    a0 = 0
    if sub.element[0] == Orb.Null:
        return (a0,a0)
    elif sub.element[1] == Orb.Null:
        return (atk, a0)
    elif sub.element[0] == sub.element[1]:
        subatk = atk/10
        return (atk, subatk)
    else:
        subatk = atk/3
        return (atk, subatk)

def totaldamage(dmg):
    return sum([sum(item) for item in dmg.values()])

def damage_by_sub(dmg,team):
    # return a list of (main attack, sub attack) pairs
    ctr = { o:0 for o in dmg.keys() }
    damage = {sub: 0 for sub in team}

    for sub in team:
        el = sub.element[0]
        el2 = sub.element[1]
        basedam = sub_dmg(sub)
        maindam = 0
        subdam = 0
        
        if basedam[0] != 0 and len(dmg[el]) is not 0:
            maindam = (dmg[el][ctr[el]])
            ctr[el] += 1
        if basedam[1] != 0 and len(dmg[el2]) is not 0:
            subdam = (dmg[el2][ctr[el2]])
            ctr[el2] += 1
        damage[sub] = (maindam,subdam)
    return damage

def rounded_prong_damage(dmg,nprong):
    newdam = dmg
    for _ in range(nprong):
        newdam = newdam*PRONG_MULT
    return newdam

def compute_damage(result,team):
    dmg = {
            Orb.R: [], Orb.G: [], Orb.B: [], Orb.L: [], Orb.D: []
            }
    matches = result[0]
    enhanced = result[1]
    rows = result[2]
    multipliers = {
            'rows': 1,
            'combos': 1,
            'prongs': 1,
            'enhance': 1,
            'leaders': 1,
            'atk': 0
            }
    mleaders = 0

    nmatch = sum(len(v) for v in matches.values())
    mcombo = 1 if nmatch==0 else 1+(nmatch-1)/4

    def add_sub_damage(dam,el,nprong):
        match = np.array(matches[el])
        nenh = np.array(enhanced[el])
        td = int(totaldamage(dmg))
        dam = float(dam)

        def mult(nen,nprong,matches):
            return mleaders*sum(enhance_multiplier(nen, team.enhance_awakenings[el])*\
                    (np.where(matches==4, (PRONG_MULT**nprong), 1))*\
                    orb_multiplier(matches))

        if len(match) != 0:
            mrows = (1+ROW_MULT*team.row_awakenings[el]*rows[el])
            multipliers['leaders'] = (multipliers['leaders']*multipliers['atk']
                    +mleaders*(dam))/(multipliers['atk']+dam)
            multipliers['rows'] = (multipliers['rows']*multipliers['atk']
                    +mrows*(dam))/(multipliers['atk']+dam)
            multipliers['combos'] = (multipliers['combos']*td+
                    mult(0,0,match)*dam)/\
                            (td+mult(0,0,3*np.ones(match.shape))*dam/len(match))
            multipliers['enhance'] = (multipliers['enhance']*td
                    +mult(nenh,nprong,match)*dam)/(td+mult(0,nprong,match)*dam)
            multipliers['prongs'] = (multipliers['prongs']*td+
                    +mult(nenh,nprong,match)*dam)/(td+mult(nenh,0,match)*dam)
            
            # Observational notes about rounding:
            #  - number of orbs and enhancement multiply the unrounded base damage, then ceil
            #  - row multiplier rounds (.5 rounds up)

            newdam = np.ones(match.shape)*(dam)

            # this matches experimental results
            newdam = np.array([AttackValue(np.ceil(float(d)*m)) for (d,m) in 
                zip(newdam, 
                    orb_multiplier(match)
                    *enhance_multiplier(nenh,team.enhance_awakenings[el]))])

            newdam = np.where(match==4, (PRONG_MULT**nprong)*newdam,newdam)
            newdam = sum(newdam)
            newdam = AttackValue(np.ceil(float(newdam)*mcombo))
            newdam = newdam*mrows
            newdam = newdam*mleaders
            dmg[el] += [newdam]

            multipliers['atk'] += dam

    for sub in team:
        basedam = sub_dmg(sub)

        if basedam[0] == 0:
            continue

        # Leader skills
        mleaders = 1
        for skill in team.lskills:
            #print(skill)
            mleaders *= skill.multiplier(sub)[1]


        # Main attack
        el = sub.element[0]
        nprong = sub.prongs
        add_sub_damage(basedam[0],el,nprong)

        if basedam[1] != 0:
            el = sub.element[1]
            add_sub_damage(basedam[1],el,nprong)

    multipliers['combos'] *= mcombo
    return (damage_by_sub(dmg,team), multipliers)

def main():
    app = QApplication([''])
    #print(app.testAttribute(Qt.AA_UseHighDpiPixmaps))
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    w = PadCalc()

    w.resize(250,150)
    w.move(300, 300)
    w.setWindowTitle('Padulator')
    w.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
