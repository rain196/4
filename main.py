
import os,json
from copy import deepcopy
from collections import Counter
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.graphics import Color,Rectangle,Line

BASE=os.path.dirname(__file__)
with open(os.path.join(BASE,"mard_291_palette.json"),encoding="utf-8") as f:
    PALETTE_DATA=json.load(f)
PALETTE={x["code"]:tuple(x["rgb"]) for x in PALETTE_DATA}
CODES=list(PALETTE)
SIZES=[32,48,64,80,96,128]

def dist(a,b):
    return .299*(a[0]-b[0])**2+.587*(a[1]-b[1])**2+.114*(a[2]-b[2])**2
def nearest(rgb): return min(CODES,key=lambda c:dist(rgb,PALETTE[c]))
def crop_square(im):
    w,h=im.size
    if w>h:
        d=(w-h)//2; return im.crop((d,0,d+h,h))
    if h>w:
        d=(h-w)//2; return im.crop((0,d,w,d+w))
    return im
def generate(path,n):
    im=crop_square(Image.open(path).convert("RGB"))
    im=im.filter(ImageFilter.MedianFilter(3)).resize((n,n),Image.Resampling.LANCZOS)
    return [[nearest(im.getpixel((x,y))) for x in range(n)] for y in range(n)]
def counts(cells): return Counter(c for r in cells for c in r)
def export_png(cells,path):
    n=len(cells); cell=34 if n<=64 else 28 if n<=96 else 22; m=70
    im=Image.new("RGB",(m+n*cell+20,m+n*cell+20),"white"); d=ImageDraw.Draw(im)
    try: font=ImageFont.truetype("DejaVuSans.ttf",max(7,cell//3)); title=ImageFont.truetype("DejaVuSans.ttf",18)
    except: font=title=ImageFont.load_default()
    d.text((m,15),f"MARD 291 · {n}×{n}",fill="black",font=title)
    for y,row in enumerate(cells):
        for x,code in enumerate(row):
            rgb=PALETTE[code]; x0=m+x*cell; y0=m+y*cell
            d.rectangle((x0,y0,x0+cell,y0+cell),fill=rgb,outline="black")
            lum=.299*rgb[0]+.587*rgb[1]+.114*rgb[2]; tc="black" if lum>155 else "white"
            bb=d.textbbox((0,0),code,font=font)
            d.text((x0+(cell-bb[2]+bb[0])/2,y0+(cell-bb[3]+bb[1])/2),code,fill=tc,font=font)
    im.save(path)

class Pattern:
    def __init__(self,cells):
        self.cells=cells; self.undo=[]; self.redo=[]
    def snap(self): return deepcopy(self.cells)
    def commit(self):
        self.undo.append(self.snap()); self.undo=self.undo[-50:]; self.redo.clear()
    def set(self,x,y,c):
        if c in PALETTE and self.cells[y][x]!=c: self.commit(); self.cells[y][x]=c
    def replace(self,a,b):
        if a==b or a not in PALETTE or b not in PALETTE or not any(a in r for r in self.cells): return
        self.commit(); self.cells=[[b if c==a else c for c in r] for r in self.cells]
    def undo_one(self):
        if self.undo: self.redo.append(self.snap()); self.cells=self.undo.pop(); return True
        return False
    def redo_one(self):
        if self.redo: self.undo.append(self.snap()); self.cells=self.redo.pop(); return True
        return False

class GridView(Widget):
    def __init__(self,root,**kw):
        super().__init__(**kw); self.root=root; self.zoom=1.; self.pan=[0,0]; self.last=None; self.moved=False
        self.bind(size=lambda *_:self.redraw(),pos=lambda *_:self.redraw())
    def redraw(self,*_):
        self.canvas.clear()
        p=self.root.pattern
        if not p:return
        n=p.size; cell=max(dp(3),min(self.width,self.height)/n*.92*self.zoom)
        sx=self.x+(self.width-n*cell)/2+self.pan[0]; sy=self.y+(self.height-n*cell)/2+self.pan[1]
        with self.canvas:
            for y,row in enumerate(p.cells):
                for x,c in enumerate(row):
                    rgb=PALETTE[c]; Color(rgb[0]/255,rgb[1]/255,rgb[2]/255)
                    Rectangle(pos=(sx+x*cell,sy+(n-1-y)*cell),size=(cell,cell))
                    Color(0,0,0,.55); Line(rectangle=(sx+x*cell,sy+(n-1-y)*cell,cell,cell),width=.35)
    def on_touch_down(self,t):
        if self.collide_point(*t.pos): self.last=t.pos; self.moved=False; return True
    def on_touch_move(self,t):
        if self.last:
            dx=t.x-self.last[0]; dy=t.y-self.last[1]
            if abs(dx)+abs(dy)>dp(5): self.moved=True; self.pan[0]+=dx; self.pan[1]+=dy; self.last=t.pos; self.redraw()
            return True
    def on_touch_up(self,t):
        if self.collide_point(*t.pos) and not self.moved: self.pick(t.pos)
        self.last=None; return True
    def pick(self,pos):
        p=self.root.pattern; n=p.size
        cell=max(dp(3),min(self.width,self.height)/n*.92*self.zoom)
        sx=self.x+(self.width-n*cell)/2+self.pan[0]; sy=self.y+(self.height-n*cell)/2+self.pan[1]
        x=int((pos[0]-sx)/cell); yy=int((pos[1]-sy)/cell); y=n-1-yy
        if 0<=x<n and 0<=y<n:self.root.color_picker(x,y)

class Root(BoxLayout):
    def __init__(self,**kw):
        super().__init__(orientation="vertical",spacing=dp(4),padding=dp(4),**kw)
        self.pattern=None; self.image_path=None
        top=BoxLayout(size_hint_y=None,height=dp(46),spacing=dp(4))
        self.sizebox=Spinner(text="64×64",values=[f"{n}×{n}" for n in SIZES]); top.add_widget(self.sizebox)
        top.add_widget(Button(text="图片",on_release=self.choose)); top.add_widget(Button(text="生成",on_release=self.generate))
        top.add_widget(Button(text="保存",on_release=self.save)); self.add_widget(top)
        self.view=GridView(self); self.add_widget(self.view)
        self.status=Label(text="选择图片 → 选择尺寸 → 生成",size_hint_y=None,height=dp(34)); self.add_widget(self.status)
        bot=BoxLayout(size_hint_y=None,height=dp(48),spacing=dp(4))
        for txt,fn in [("↶",self.undo),("↷",self.redo),("统计",self.stats),("替换",self.replace),("PNG",self.png)]:
            bot.add_widget(Button(text=txt,on_release=fn))
        self.add_widget(bot)
    def choose(self,*_):
        fc=FileChooserListView(filters=["*.png","*.jpg","*.jpeg","*.webp"])
        box=BoxLayout(orientation="vertical"); box.add_widget(fc)
        row=BoxLayout(size_hint_y=None,height=dp(46)); box.add_widget(row)
        pop=Popup(title="选择图片",content=box,size_hint=(.96,.92))
        row.add_widget(Button(text="取消",on_release=pop.dismiss))
        ok=Button(text="使用"); row.add_widget(ok)
        def use(*_):
            if fc.selection:self.image_path=fc.selection[0]; self.status.text="已选择 "+os.path.basename(self.image_path); pop.dismiss()
        ok.bind(on_release=use); pop.open()
    def generate(self,*_):
        if not self.image_path:self.status.text="请先选择图片"; return
        n=int(self.sizebox.text.split("×")[0]); self.status.text="生成中..."
        Clock.schedule_once(lambda dt:self._generate(n),.05)
    def _generate(self,n):
        try:
            self.pattern=Pattern(generate(self.image_path,n)); self.view.zoom=1.; self.view.pan=[0,0]; self.view.redraw(); self.update()
        except Exception as e:self.status.text="生成失败: "+str(e)
    def update(self):
        if self.pattern:
            self.status.text=f"{self.pattern.size}×{self.pattern.size} · {len(counts(self.pattern.cells))}种颜色 · {self.pattern.size**2}颗"
    def color_picker(self,x,y):
        old=self.pattern.cells[y][x]
        box=BoxLayout(orientation="vertical",spacing=dp(4),padding=dp(5))
        box.add_widget(Label(text=f"格子 {x+1},{y+1} · 当前 {old}",size_hint_y=None,height=dp(32)))
        search=TextInput(hint_text="搜索色号，如 H7",multiline=False,size_hint_y=None,height=dp(40)); box.add_widget(search)
        grid=GridLayout(cols=5,spacing=dp(3),size_hint_y=None); grid.bind(minimum_height=grid.setter("height")); sc=ScrollView(); sc.add_widget(grid); box.add_widget(sc)
        pop=Popup(title="MARD 291 色卡",content=box,size_hint=(.95,.9))
        def refresh(*_):
            q=search.text.upper().strip(); grid.clear_widgets()
            for c in ([c for c in CODES if q in c] if q else CODES):
                rgb=PALETTE[c]; b=Button(text=c,size_hint_y=None,height=dp(40),background_normal="",background_color=tuple(v/255 for v in rgb)+(1,))
                b.color=(0,0,0,1) if .299*rgb[0]+.587*rgb[1]+.114*rgb[2]>155 else (1,1,1,1)
                b.bind(on_release=lambda _,cc=c:(self.pattern.set(x,y,cc),pop.dismiss(),self.view.redraw(),self.update()))
                grid.add_widget(b)
        search.bind(text=refresh); refresh(); pop.open()
    def replace(self,*_):
        if not self.pattern:return
        used=sorted(counts(self.pattern.cells)); box=BoxLayout(orientation="vertical",spacing=dp(5),padding=dp(7))
        a=Spinner(text=used[0],values=used,size_hint_y=None,height=dp(40)); b=TextInput(hint_text="新色号",multiline=False,size_hint_y=None,height=dp(40))
        box.add_widget(Label(text="原色号")); box.add_widget(a); box.add_widget(Label(text="替换为")); box.add_widget(b)
        ok=Button(text="替换全部",size_hint_y=None,height=dp(44)); box.add_widget(ok); pop=Popup(title="整色替换",content=box,size_hint=(.85,.55))
        def do(*_):
            c=b.text.upper().strip()
            if c in PALETTE:self.pattern.replace(a.text,c); pop.dismiss(); self.view.redraw(); self.update()
        ok.bind(on_release=do); pop.open()
    def stats(self,*_):
        if not self.pattern:return
        box=BoxLayout(orientation="vertical"); sc=ScrollView(); g=GridLayout(cols=2,size_hint_y=None); g.bind(minimum_height=g.setter("height"))
        for c,n in sorted(counts(self.pattern.cells).items(),key=lambda z:(-z[1],z[0])):
            rgb=PALETTE[c]; b=Button(text=c,size_hint_y=None,height=dp(36),background_normal="",background_color=tuple(v/255 for v in rgb)+(1,))
            g.add_widget(b); g.add_widget(Label(text=f"×{n}",size_hint_y=None,height=dp(36)))
        sc.add_widget(g); box.add_widget(sc); pop=Popup(title="材料统计",content=box,size_hint=(.8,.8)); pop.open()
    def undo(self,*_):
        if self.pattern and self.pattern.undo_one():self.view.redraw();self.update()
    def redo(self,*_):
        if self.pattern and self.pattern.redo_one():self.view.redraw();self.update()
    def save(self,*_):
        if not self.pattern:return
        path=os.path.join(App.get_running_app().user_data_dir,"mard_project.json")
        with open(path,"w",encoding="utf-8") as f:json.dump({"version":"4.2","palette":"MARD 291","size":self.pattern.size,"cells":self.pattern.cells,"source":os.path.basename(self.image_path or "")},f,ensure_ascii=False)
        self.status.text="项目已保存"
    def png(self,*_):
        if not self.pattern:return
        path=os.path.join(App.get_running_app().user_data_dir,"mard_pattern.png"); export_png(self.pattern.cells,path); self.status.text="PNG 已导出"

class AppMain(App):
    def build(self): self.title="MARD 拼豆图纸 V4.2"; return Root()
if __name__=="__main__": AppMain().run()
