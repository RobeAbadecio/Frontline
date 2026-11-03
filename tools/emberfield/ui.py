"""Original FDF authored for the existing Warcraft-compatible HUD contracts."""
from pathlib import Path

FONT='Emberfield\\Fonts\\ui.ttf'
TEX='Emberfield\\Textures\\'

def frame(kind,name,body='',w=None,h=None,x=None,y=None):
    props=''
    if w is not None:props+=f'Width {w}, '
    if h is not None:props+=f'Height {h}, '
    if x is not None:props+=f'Anchor TOPLEFT,{x},{-y}, '
    return f'Frame "{kind}" "{name}" {{ {props}{body} }}\n'

def text(name,value='',w=.25,h=.024,x=0,y=0,size=.012):
    return frame('TEXT',name,f'Font "MasterFont",{size}, FontColor 0.93 0.89 0.78 1, Text "{value}",',w,h,x,y)

def backdrop(name='Backdrop',file='dialog'):
    return frame('BACKDROP',name,f'SetAllPoints, BackdropBackground "{TEX}{file}.blp",')

def button(name,label,x,y,w=.26,h=.041):
    return frame('GLUETEXTBUTTON',name,f'ControlBackdrop \"{name}Background\", ControlPushedBackdrop \"{name}Pushed\", '+backdrop(name+'Background','button')+backdrop(name+'Pushed','button-pressed')+text(name+'Text',label,w-.02,h,.01,0,.012),w,h,x,y)

def write(root):
    def put(name,data):
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(data)
    skin='[Default]\n'
    for k in ['MasterFont','MessageFont','ChatFont']:skin+=f'{k}={FONT}\n'
    icons={'GoldIcon':'gather','LumberIcon':'timber','SupplyIcon':'supply','ToolTipGoldIcon':'gather','ToolTipLumberIcon':'timber','ToolTipSupplyIcon':'supply','ToolTipManaIcon':'spell','MinimapResourceTexture':'ore','MinimapEntangledResourceTexture':'ore','MinimapHauntedResourceTexture':'ore','MinimapHeroTexture':'group','MinimapNeutralTexture':'hold'}
    for k,v in icons.items():skin+=f'{k}=Emberfield\\Icons\\{v}.blp\n'
    skin+='InfoPanelIconDamageNormal=Emberfield\\Icons\\attack.blp\nInfoPanelIconArmorNormal=Emberfield\\Icons\\hold.blp\nInfoPanelIconFood=Emberfield\\Icons\\supply.blp\nInfoPanelIconGold=Emberfield\\Icons\\gather.blp\n'
    skin+='ControlGroupBar=UI\\FrameDef\\UI\\ControlGroupBar.fdf\n'
    skin+='CommandButtonDisabledArtPath=Emberfield\\Icons\\Disabled\\\n'
    for i in range(1,7):skin+=f'ConsoleTexture0{i}={TEX}hud.blp\n'
    for k in ['SimpleHpBarConsoleSmall','SimpleHpBarConsole','SimpleManaBarConsoleSmall','SimpleManaBarConsole','SimpleBuildTimeIndicator','SimpleProgressBarConsole','SimpleXpBarConsole']:skin+=f'{k}={TEX}bar.blp\n'
    for k in ['SimpleBuildTimeIndicatorBorder','SimpleProgressBarBorder','SimpleXpBarBorder']:skin+=f'{k}={TEX}bar-border.blp\n'
    skin+=f'ConsoleInventoryCoverTexture={TEX}inventory-cover.blp\nToolTipBackground={TEX}dialog.blp\nToolTipBorder={TEX}bar-border.blp\n'
    put('UI/war3skins.txt',skin)
    strings={'GOLD':'Ore','LUMBER':'Timber','FOOD':'Supply','UPKEEP_NONE':'READY','GAMEOVER_VICTORY_MSG':'Victory','GAMEOVER_DEFEAT_MSG':'Defeat','GAMEOVER_RESTART':'Play Again','COLON_DAMAGE':'Damage:','COLON_ARMOR':'Armor:','COLON_FOOD':'Supply:','COLON_FOOD_PROVIDED':'Capacity:','COLON_GOLD':'Ore:','COLON_STRENGTH':'Strength:','COLON_AGILITY':'Agility:','COLON_INTELLECT':'Intellect:','COLON_STATUS':'Status:'}
    catalog='StringList { '+''.join(f'{k} "{v}", ' for k,v in strings.items())+'}\n'
    put('UI/FrameDef/GlobalStrings.fdf',catalog);put('UI/FrameDef/InfoPanelStrings.fdf',catalog)
    console=f'''Texture {{ File "{TEX}hud.blp", Width 0.8, Height 0.15, Anchor BOTTOMLEFT,0,0, }}
    Texture {{ File "{TEX}top.blp", Width 0.8, Height 0.038, Anchor TOPLEFT,0,0, }}'''
    put('UI/FrameDef/UI/ConsoleUI.fdf',frame('SIMPLEFRAME','ConsoleUI',console))
    resources=''
    for i,(key,label,symbol) in enumerate([('Gold','ORE','gather'),('Lumber','TIMBER','timber'),('Supply','SUPPLY','supply'),('Upkeep','EMBERFIELD','')]):
        x=i*.094
        if symbol:resources+=f'Texture {{ File "Emberfield\\Icons\\{symbol}.blp", Width 0.021, Height 0.023, Anchor TOPLEFT,{x},-0.007, }}'
        resources+=f'String "ResourceBar{key}Text" {{ Font "MasterFont",0.012, FontColor 0.95 0.91 0.8 1, Width 0.067, Height 0.03, Text "0", Anchor TOPLEFT,{x+.024},-0.004, }}'
    put('UI/FrameDef/UI/ResourceBar.fdf',frame('SIMPLEFRAME','ResourceBarFrame',resources,.39,.038))
    # Only Menu is exposed; other required binding slots have no geometry.
    upper=frame('SIMPLEBUTTON','UpperButtonBarMenuButton','NormalTexture "EmberMenuNormal", PushedTexture "EmberMenuPushed", NormalText "EmberMenuText" "MENU",',.082,.034,.008,.002)
    upper+=''.join(frame('SIMPLEBUTTON','UpperButtonBar'+n+'Button','',0,0,-2,0) for n in ['Quests','Allies','Chat'])
    put('UI/FrameDef/UI/UpperButtonBar.fdf',f'Texture "EmberMenuNormal" {{ File "{TEX}button.blp", }} Texture "EmberMenuPushed" {{ File "{TEX}button-pressed.blp", }} String "EmberMenuText" {{ Font "MasterFont",0.012, FontColor 0.94 0.89 0.76 1, }}'+frame('SIMPLEFRAME','UpperButtonBarFrame',upper,.34,.038))
    groups=''
    for i in range(1,4):
        for name,label,x in [('Recall',str(i),.119+(i-1)*.084),('Assign','+'+str(i),.160+(i-1)*.084)]:
            groups+=frame('SIMPLEBUTTON',f'ControlGroup{i}{name}',f'NormalTexture "EmberMenuNormal", PushedTexture "EmberMenuPushed", NormalText "EmberMenuText" "{label}",',.037,.034,x,.002)
    put('UI/FrameDef/UI/ControlGroupBar.fdf',frame('SIMPLEFRAME','ControlGroupBarFrame',groups,.4,.038))
    # Legacy detail binding supplies readable name and stats without new HUD code.
    stats=''
    for i,(label,value,caption) in enumerate([('AttackLabel1','AttackValue1','Damage:'),('DefenseLabel','DefenseValue','Armor:'),('SpeedTitle','SpeedValue','Speed:')]):
        stats+=text(label,caption,.07,.018,0,.033+i*.022,.011)+text(value,'',.08,.018,.073,.033+i*.022,.011)
    for n in ['ProgressIndicator','ClassValue','AttackLabel2','AttackValue2','RangeTitle1','RangeValue1','RangeTitle2','RangeValue2','IconBackdrop1','IconValue1','IconBackdrop2','IconValue2','IconBackdrop3','IconValue3','IconBackdrop4','IconValue4']:
        stats+=frame('FRAME' if 'Backdrop' in n or n=='ProgressIndicator' else 'TEXT',n,'',0,0)
    detail=text('NameValue','',.19,.027,0,0,.014)+frame('FRAME','HeroLevelBar','',0,0)+frame('FRAME','UnitStatsPanel',stats,.18,.12)
    put('UI/FrameDef/UI/InfoPanelTemplates.fdf','// Original Emberfield detail frames.\n')
    put('UI/FrameDef/UI/InfoPanelUnitDetail.fdf',frame('FRAME','InfoPanelUnitDetail',detail,.18,.12))
    # Pause menu uses the engine's existing modal pause, restart and resume actions.
    main=text('WouldTheRealOptionsTitleTextPleaseStandUp','EMBERFIELD',.28,.035,.035,.018,.019)
    inside=button('ReturnButton','Return to Battle',.035,.071)+button('EndGameButton','Restart / Leave',.035,.124)
    for n in ['Pause','SaveGame','LoadGame','Options','Help','Tips']:
        inside+=frame('GLUETEXTBUTTON',n+'Button',text(n+'ButtonText','',0,0),0,0,-2,0)
    main+=frame('FRAME','InsideMainPanel',inside,.33,.3)
    end=text('EndGameTitleText','MATCH',.28,.03,.035,.015,.018)
    end+=button('RestartButton','Restart Match',.035,.065)+button('QuitButton','Leave Match',.035,.118)+button('ExitButton','Exit App',.035,.171)+button('PreviousButton','Back',.035,.224)
    confirm=text('ConfirmQuitTitleText','EXIT EMBERFIELD',.28,.035,.035,.02,.017)+text('ConfirmQuitMessageText','Leave the current match?',.28,.05,.035,.067)
    confirm+=button('ConfirmQuitQuitButton','Exit',.035,.14)+button('ConfirmQuitCancelButton','Back',.035,.195)
    panels=frame('FRAME','MainPanel',main,.33,.3)+frame('FRAME','EndGamePanel',frame('FRAME','InsideEndGamePanel',end,.33,.3),.33,.3)
    panels+=frame('FRAME','ConfirmQuitPanel',frame('FRAME','InsideConfirmQuitPanel',confirm,.33,.3),.33,.3)
    for n,children in [('Help',['HelpTitleText','HelpTextArea','HelpOKButton']),('Tips',['TipsTitleText','TipsTextArea','TipsBackButton','TipsNextButton','TipsOKButton'])]:
        body=''.join(button(c,'',0,0,0,0) if 'Button' in c else text(c,'',0,0) for c in children)
        panels+=frame('FRAME',n+'Panel',frame('FRAME','Inside'+n+'Panel',body,0,0),0,0)
    put('UI/FrameDef/UI/EscMenuSaveGamePanel.fdf',frame('FRAME','EscMenuSaveGamePanel','',0,0))
    put('UI/FrameDef/UI/EscMenuTemplates.fdf','// Original menu art.\n')
    put('UI/FrameDef/UI/EscMenuMainPanel.fdf',frame('FRAME','EscMenuMainPanel',panels,.33,.3)+frame('BACKDROP','EscMenuBackdrop',f'SetAllPoints, BackdropBackground "{TEX}dialog.blp",'))
    result=backdrop('GameResultBackdrop')+text('GameResultText','',.27,.045,.035,.02,.024)
    for i,n in enumerate(['Continue','Restart','Quit']):result+=button('GameResult'+n+'Button',n,.035,.08+i*.054)
    put('UI/FrameDef/UI/GameResultDialog.fdf',frame('DIALOG','GameResultDialog',result,.33,.29))


def simple_info(root):
    def put(name,data):
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(data)
    unit=text('SimpleNameValue','',.18,.026,0,0,.014)
    unit+=frame('SIMPLESTATUSBAR','SimpleHeroLevelBar','',.18,.01,0,.027)
    unit+=frame('SIMPLESTATUSBAR','SimpleProgressIndicator','',.18,.01,0,.028)
    unit+=frame('FRAME','SimpleUnitStatsPanel',text('SimpleClassValue','',0,0),.18,.09,0,.027)
    result=frame('FRAME','SimpleInfoPanelUnitDetail',unit,.18,.12)
    building=text('SimpleBuildingNameValue','',.18,.024,0,0,.014)+text('SimpleBuildingDescriptionValue','',.18,.02,0,.026,.011)
    building+=text('SimpleBuildingActionLabel','',.15,.02,.049,.026,.011)
    building+=frame('SIMPLESTATUSBAR','SimpleBuildTimeIndicator','',.10538,.0103,.049,.049)
    building+=frame('FRAME','ARTWORK',frame('FRAME','SimpleBuildQueueBackdrop','',.18,.09),.18,.09)
    result+=frame('FRAME','SimpleInfoPanelBuildingDetail',building,.18,.12)
    result+=frame('FRAME','SimpleInfoPanelItemDetail',text('SimpleItemNameValue')+text('SimpleItemDescriptionValue'),.18,.12)
    for kind,caption in [('Damage','Damage:'),('Armor','Armor:'),('Rank','Rank:'),('Food','Supply:'),('Gold','Ore:')]:
        body=frame('TEXTURE','InfoPanelIconBackdrop','',.024,.024,0,0)+text('InfoPanelIconLevel','',.015,.012,.008,.015,.009)
        body+=text('InfoPanelIconLabel',caption,.07,.014,.032,0,.010)+text('InfoPanelIconValue','',.07,.018,.032,.014,.012)
        result+=frame('FRAME','SimpleInfoPanelIcon'+kind,body,.1,.03125)
    hero=frame('TEXTURE','InfoPanelIconHeroIcon','',.019,.019,0,0)
    attributes=''
    for row,attribute in enumerate(('Strength','Agility','Intellect')):
        attributes+=text('InfoPanelIconHero'+attribute+'Label','',.055,.018,.022,row*.020,.009)
        attributes+=text('InfoPanelIconHero'+attribute+'Value','',.022,.018,.078,row*.020,.011)
    hero+=frame('FRAME','SimpleInfoPanelIconHeroText',attributes,.10,.060,0,0)
    result+=frame('FRAME','SimpleInfoPanelIconHero',hero,.10,.0625)
    ally=''.join(frame('TEXTURE' if 'Icon' in n else 'TEXT',n,'',0,0) for n in ['InfoPanelIconAllyTitle','InfoPanelIconAllyGoldIcon','InfoPanelIconAllyGoldValue','InfoPanelIconAllyWoodIcon','InfoPanelIconAllyWoodValue','InfoPanelIconAllyFoodIcon','InfoPanelIconAllyFoodValue','InfoPanelIconAllyUpkeep'])
    result+=frame('FRAME','SimpleInfoPanelIconAlly',ally,0,0)
    result+=frame('FRAME','SimpleInfoPanelCargoDetail',text('SimpleHoldNameValue','',0,0)+text('SimpleHoldDescriptionValue','',0,0),.18,.12)
    put('UI/FrameDef/UI/SimpleInfoPanel.fdf',result)
