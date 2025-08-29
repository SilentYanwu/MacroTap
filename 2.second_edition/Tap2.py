import time
import threading
import json
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from pynput import mouse, keyboard
from pynput.mouse import Button
from pynput.keyboard import Key, KeyCode, Listener
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import os
from typing import List, Dict, Any, Optional

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AutoClicker")

# 字符串资源类，便于国际化
class Strings:
    TITLE = "多步骤连点器"
    STATUS_READY = "状态: 尚未使用"
    STATUS_PREPARING = "状态: 准备中"
    STATUS_RUNNING = "状态: 正在使用"
    STATUS_STOPPED = "状态: 已停止"
    HOTKEY_INFO = "快捷键: F键开始 | Q键停止\n开始后有5秒延迟时间，请切换到目标窗口"
    STEP_DELAY = "步骤间隔(秒):"
    LOOP_DELAY = "循环间隔(秒):"
    LOOP_COUNT = "循环次数(0=无限):"
    SET = "设置"
    ADD_STEP = "添加步骤"
    EDIT_STEP = "编辑步骤"
    REMOVE_STEP = "删除步骤"
    CLEAR_STEPS = "清空步骤"
    START = "开始 (F)"
    STOP = "停止 (Q)"
    STEP_TYPE = "步骤类型:"
    MOUSE_BUTTON = "鼠标按钮:"
    ACTION = "动作:"
    KEY = "按键:"
    DELAY = "延时(秒):"
    CONFIRM = "确认"
    CANCEL = "取消"
    SAVE_CONFIG = "保存配置"
    LOAD_CONFIG = "加载配置"
    STEP_LIST = "步骤列表"
    DELAY_SETTINGS = "间隔时间设置"
    CONTROL = "控制"
    MOUSE = "鼠标"
    KEYBOARD = "键盘"
    DELAY_STEP = "延时"
    LEFT = "左键"
    RIGHT = "右键"
    MIDDLE = "中键"
    CLICK = "点击"
    PRESS = "按下"
    RELEASE = "释放"
    LOAD_BG = "加载背景"
    NO_BG = "无背景"

class StepManager:
    """步骤管理器"""
    def __init__(self):
        self.steps = []
        
    def add_step(self, step_data: Dict[str, Any]) -> None:
        """添加步骤"""
        self.steps.append(step_data)
        
    def remove_step(self, index: int) -> Optional[Dict[str, Any]]:
        """删除步骤"""
        if 0 <= index < len(self.steps):
            return self.steps.pop(index)
        return None
        
    def clear(self) -> None:
        """清空所有步骤"""
        self.steps.clear()
        
    def get_step(self, index: int) -> Optional[Dict[str, Any]]:
        """获取指定步骤"""
        if 0 <= index < len(self.steps):
            return self.steps[index]
        return None
        
    def update_step(self, index: int, step_data: Dict[str, Any]) -> bool:
        """更新步骤"""
        if 0 <= index < len(self.steps):
            self.steps[index] = step_data
            return True
        return False
        
    def move_step(self, from_index: int, to_index: int) -> bool:
        """移动步骤位置"""
        if 0 <= from_index < len(self.steps) and 0 <= to_index < len(self.steps):
            step = self.steps.pop(from_index)
            self.steps.insert(to_index, step)
            return True
        return False
        
    def save_to_file(self, filename: str) -> bool:
        """保存步骤到文件"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.steps, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"保存步骤到文件失败: {e}")
            return False
            
    def load_from_file(self, filename: str) -> bool:
        """从文件加载步骤"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                self.steps = json.load(f)
            return True
        except Exception as e:
            logger.error(f"从文件加载步骤失败: {e}")
            return False

class AutoClicker:
    def __init__(self, root):
        self.root = root
        self.setup_window()
        self.setup_managers()
        self.load_config()
        self.create_widgets()
        self.setup_listeners()
        self.add_default_steps()
        
    def setup_window(self):
        """设置窗口属性"""
        self.root.title(Strings.TITLE)
        self.root.geometry("900x650")
        self.root.resizable(True, True)
        self.root.attributes('-alpha', 0.9)
        
        # 设置窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def setup_managers(self):
        """初始化管理器"""
        self.step_manager = StepManager()
        self.config = {
            'step_delay': 0.5,
            'loop_delay': 0.5,
            'loop_count': 0,  # 0表示无限循环
            'start_hotkey': 'f',
            'stop_hotkey': 'q',
            'bg_image': None
        }
        self.is_running = False
        self.is_counting_down = False
        self.current_loop = 0
        
    def load_config(self):
        """加载配置"""
        try:
            if os.path.exists('config.json'):
                with open('config.json', 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    self.config.update(saved_config)
                    
                # 加载步骤
                if os.path.exists('steps.json'):
                    self.step_manager.load_from_file('steps.json')
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            
    def save_config(self):
        """保存配置"""
        try:
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
                
            # 保存步骤
            self.step_manager.save_to_file('steps.json')
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            
    def on_close(self):
        """窗口关闭时的清理工作"""
        self.save_config()
        if hasattr(self, 'keyboard_listener') and self.keyboard_listener and self.keyboard_listener.is_alive():
            self.keyboard_listener.stop()
        self.root.destroy()
        
    def create_widgets(self):
        """创建界面组件"""
        # 创建主框架
        self.main_frame = tk.Frame(self.root, bg="#f0f0f0", bd=2, relief="raised")
        self.main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # 状态指示器
        self.status_indicator = tk.Frame(self.main_frame, height=30, bg="green")
        self.status_indicator.pack(fill="x", pady=5)
        
        self.status_text = tk.Label(
            self.status_indicator, 
            text=Strings.STATUS_READY, 
            bg="green", 
            fg="white", 
            font=("微软雅黑", 12, "bold")
        )
        self.status_text.pack(expand=True)
        
        # 标题
        title_label = ttk.Label(self.main_frame, text=Strings.TITLE, font=("微软雅黑", 16, "bold"))
        title_label.pack(pady=10)
        
        # 说明
        desc_label = ttk.Label(self.main_frame, 
                              text=Strings.HOTKEY_INFO,
                              font=("微软雅黑", 10), justify=tk.CENTER)
        desc_label.pack(pady=5)
        
        # 间隔时间设置框架
        delay_frame = ttk.LabelFrame(self.main_frame, text=Strings.DELAY_SETTINGS)
        delay_frame.pack(pady=10, padx=20, fill="x")
        
        # 步骤间隔设置
        step_delay_frame = ttk.Frame(delay_frame)
        step_delay_frame.pack(pady=5, fill="x", padx=10)
        
        step_delay_label = ttk.Label(step_delay_frame, text=Strings.STEP_DELAY)
        step_delay_label.grid(row=0, column=0, padx=5, sticky="w")
        
        self.step_delay_var = tk.StringVar(value=str(self.config['step_delay']))
        step_delay_entry = ttk.Entry(step_delay_frame, textvariable=self.step_delay_var, width=10)
        step_delay_entry.grid(row=0, column=1, padx=5)
        
        set_step_delay_btn = ttk.Button(step_delay_frame, text=Strings.SET, command=self.set_step_delay)
        set_step_delay_btn.grid(row=0, column=2, padx=5)
        
        # 循环间隔设置
        loop_delay_frame = ttk.Frame(delay_frame)
        loop_delay_frame.pack(pady=5, fill="x", padx=10)
        
        loop_delay_label = ttk.Label(loop_delay_frame, text=Strings.LOOP_DELAY)
        loop_delay_label.grid(row=0, column=0, padx=5, sticky="w")
        
        self.loop_delay_var = tk.StringVar(value=str(self.config['loop_delay']))
        loop_delay_entry = ttk.Entry(loop_delay_frame, textvariable=self.loop_delay_var, width=10)
        loop_delay_entry.grid(row=0, column=1, padx=5)
        
        set_loop_delay_btn = ttk.Button(loop_delay_frame, text=Strings.SET, command=self.set_loop_delay)
        set_loop_delay_btn.grid(row=0, column=2, padx=5)
        
        # 循环次数设置
        loop_count_frame = ttk.Frame(delay_frame)
        loop_count_frame.pack(pady=5, fill="x", padx=10)
        
        loop_count_label = ttk.Label(loop_count_frame, text=Strings.LOOP_COUNT)
        loop_count_label.grid(row=0, column=0, padx=5, sticky="w")
        
        self.loop_count_var = tk.StringVar(value=str(self.config['loop_count']))
        loop_count_entry = ttk.Entry(loop_count_frame, textvariable=self.loop_count_var, width=10)
        loop_count_entry.grid(row=0, column=1, padx=5)
        
        set_loop_count_btn = ttk.Button(loop_count_frame, text=Strings.SET, command=self.set_loop_count)
        set_loop_count_btn.grid(row=0, column=2, padx=5)
        
        # 步骤框架
        steps_frame = ttk.LabelFrame(self.main_frame, text=Strings.STEP_LIST)
        steps_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        # 使用Treeview显示步骤列表
        columns = ("序号", "类型", "详情")
        self.steps_tree = ttk.Treeview(steps_frame, columns=columns, show="headings", height=6)
        
        for col in columns:
            self.steps_tree.heading(col, text=col)
            self.steps_tree.column(col, width=100)
        
        self.steps_tree.pack(pady=10, padx=10, fill="both", expand=True)
        
        # 绑定双击编辑事件
        self.steps_tree.bind("<Double-1>", self.edit_step_event)
        
        # 按钮框架
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(pady=10)
        
        # 添加步骤按钮
        add_step_btn = ttk.Button(button_frame, text=Strings.ADD_STEP, command=self.add_step_window)
        add_step_btn.grid(row=0, column=0, padx=5)
        
        # 编辑步骤按钮
        edit_step_btn = ttk.Button(button_frame, text=Strings.EDIT_STEP, command=self.edit_step)
        edit_step_btn.grid(row=0, column=1, padx=5)
        
        # 删除步骤按钮
        remove_step_btn = ttk.Button(button_frame, text=Strings.REMOVE_STEP, command=self.remove_step)
        remove_step_btn.grid(row=0, column=2, padx=5)
        
        # 清空步骤按钮
        clear_steps_btn = ttk.Button(button_frame, text=Strings.CLEAR_STEPS, command=self.clear_steps)
        clear_steps_btn.grid(row=0, column=3, padx=5)
        
        # 控制按钮框架
        control_frame = ttk.LabelFrame(self.main_frame, text=Strings.CONTROL)
        control_frame.pack(pady=10, padx=20, fill="x")
        
        control_btn_frame = ttk.Frame(control_frame)
        control_btn_frame.pack(pady=10)
        
        # 开始按钮
        self.start_btn = ttk.Button(control_btn_frame, text=Strings.START, command=self.start_autoclicker)
        self.start_btn.grid(row=0, column=0, padx=5)
        
        # 停止按钮
        self.stop_btn = ttk.Button(control_btn_frame, text=Strings.STOP, command=self.stop_autoclicker, state="disabled")
        self.stop_btn.grid(row=0, column=1, padx=5)
        
        # 保存/加载配置按钮
        save_config_btn = ttk.Button(control_btn_frame, text=Strings.SAVE_CONFIG, command=self.save_config)
        save_config_btn.grid(row=0, column=2, padx=5)
        
        load_config_btn = ttk.Button(control_btn_frame, text=Strings.LOAD_CONFIG, command=self.load_config_ui)
        load_config_btn.grid(row=0, column=3, padx=5)
        
        # 加载背景按钮
        load_bg_btn = ttk.Button(control_btn_frame, text=Strings.LOAD_BG, command=self.load_background)
        load_bg_btn.grid(row=0, column=4, padx=5)
        
        no_bg_btn = ttk.Button(control_btn_frame, text=Strings.NO_BG, command=self.remove_background)
        no_bg_btn.grid(row=0, column=5, padx=5)
        
        # 倒计时标签
        self.countdown_label = ttk.Label(self.main_frame, text="", font=("微软雅黑", 12, "bold"), foreground="blue")
        self.countdown_label.pack(pady=5)
        
        # 循环计数标签
        self.loop_count_label = ttk.Label(self.main_frame, text="", font=("微软雅黑", 10), foreground="green")
        self.loop_count_label.pack(pady=2)
        
        # 更新步骤列表显示
        self.update_steps_tree()
    
    def setup_listeners(self):
        """设置键盘监听器"""
        self.start_hotkey = {KeyCode.from_char(self.config['start_hotkey'])}
        self.stop_hotkeys = {KeyCode.from_char(self.config['stop_hotkey'])}
        
        self.keyboard_listener = Listener(on_press=self.on_key_press)
        self.keyboard_listener.daemon = True
        self.keyboard_listener.start()
    
    def set_step_delay(self):
        """设置步骤间隔时间"""
        try:
            delay = float(self.step_delay_var.get())
            if delay < 0 or delay > 60:
                messagebox.showerror("错误", "延迟时间必须在0-60秒之间")
                return
            self.config['step_delay'] = delay
            messagebox.showinfo("成功", f"步骤间延迟已设置为 {delay} 秒")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
    
    def set_loop_delay(self):
        """设置循环间隔时间"""
        try:
            delay = float(self.loop_delay_var.get())
            if delay < 0 or delay > 3600:
                messagebox.showerror("错误", "延迟时间必须在0-3600秒之间")
                return
            self.config['loop_delay'] = delay
            messagebox.showinfo("成功", f"循环间延迟已设置为 {delay} 秒")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
    
    def set_loop_count(self):
        """设置循环次数"""
        try:
            count = int(self.loop_count_var.get())
            if count < 0:
                messagebox.showerror("错误", "循环次数不能为负数")
                return
            self.config['loop_count'] = count
            messagebox.showinfo("成功", f"循环次数已设置为 {count}")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的整数")
    
    def update_status_indicator(self, status, color):
        """更新状态指示器"""
        def update():
            self.status_indicator.config(bg=color)
            self.status_text.config(
                text=f"状态: {status}", 
                bg=color, 
                fg="white"
            )
        self.root.after(0, update)
    
    def add_default_steps(self):
        """添加默认步骤"""
        self.step_manager.add_step({"type": "mouse", "button": "right", "action": "click"})
        self.step_manager.add_step({"type": "keyboard", "key": "esc", "action": "press"})
        self.step_manager.add_step({"type": "mouse", "button": "left", "action": "click"})
        
        self.update_steps_tree()
    
    def update_steps_tree(self):
        """更新步骤树形视图"""
        # 清空现有项目
        for item in self.steps_tree.get_children():
            self.steps_tree.delete(item)
        
        # 添加新项目
        for i, step in enumerate(self.step_manager.steps):
            if step["type"] == "mouse":
                details = f"{step['button']}键 {step['action']}"
                self.steps_tree.insert("", "end", values=(i+1, "鼠标", details))
            elif step["type"] == "keyboard":
                details = f"{step['key']}键 {step['action']}"
                self.steps_tree.insert("", "end", values=(i+1, "键盘", details))
            elif step["type"] == "delay":
                details = f"{step['duration']}秒"
                self.steps_tree.insert("", "end", values=(i+1, "延时", details))
    
    def add_step_window(self):
        """添加步骤窗口"""
        window = tk.Toplevel(self.root)
        window.title(Strings.ADD_STEP)
        window.geometry("300x300")
        window.resizable(False, False)
        
        # 步骤类型选择
        type_label = ttk.Label(window, text=Strings.STEP_TYPE)
        type_label.pack(pady=5)
        
        step_type = tk.StringVar(value="mouse")
        type_combobox = ttk.Combobox(window, textvariable=step_type, 
                                    values=[Strings.MOUSE, Strings.KEYBOARD, Strings.DELAY_STEP], 
                                    state="readonly")
        type_combobox.pack(pady=5)
        
        # 鼠标步骤框架
        mouse_frame = ttk.Frame(window)
        
        mouse_button_label = ttk.Label(mouse_frame, text=Strings.MOUSE_BUTTON)
        mouse_button_label.grid(row=0, column=0, padx=5)
        
        mouse_button = tk.StringVar(value=Strings.LEFT)
        mouse_combobox = ttk.Combobox(mouse_frame, textvariable=mouse_button, 
                                     values=[Strings.LEFT, Strings.RIGHT, Strings.MIDDLE], 
                                     state="readonly")
        mouse_combobox.grid(row=0, column=1, padx=5)
        
        mouse_action_label = ttk.Label(mouse_frame, text=Strings.ACTION)
        mouse_action_label.grid(row=1, column=0, padx=5)
        
        mouse_action = tk.StringVar(value=Strings.CLICK)
        mouse_action_combobox = ttk.Combobox(mouse_frame, textvariable=mouse_action, 
                                            values=[Strings.CLICK, Strings.PRESS, Strings.RELEASE], 
                                            state="readonly")
        mouse_action_combobox.grid(row=1, column=1, padx=5)
        
        # 键盘步骤框架
        keyboard_frame = ttk.Frame(window)
        
        keyboard_key_label = ttk.Label(keyboard_frame, text=Strings.KEY)
        keyboard_key_label.grid(row=0, column=0, padx=5)
        
        keyboard_key = tk.StringVar(value="a")
        keyboard_combobox = ttk.Combobox(keyboard_frame, textvariable=keyboard_key, 
                                        values=[
                                            "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", 
                                            "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
                                            "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
                                            "esc", "enter", "space", "tab", "shift", "ctrl", "alt"
                                        ], state="readonly")
        keyboard_combobox.grid(row=0, column=1, padx=5)
        
        keyboard_action_label = ttk.Label(keyboard_frame, text=Strings.ACTION)
        keyboard_action_label.grid(row=1, column=0, padx=5)
        
        keyboard_action = tk.StringVar(value=Strings.PRESS)
        keyboard_action_combobox = ttk.Combobox(keyboard_frame, textvariable=keyboard_action, 
                                               values=[Strings.PRESS, Strings.RELEASE], 
                                               state="readonly")
        keyboard_action_combobox.grid(row=1, column=1, padx=5)
        
        # 延时步骤框架
        delay_frame = ttk.Frame(window)
        
        delay_label = ttk.Label(delay_frame, text=Strings.DELAY)
        delay_label.grid(row=0, column=0, padx=5)
        
        delay_duration = tk.StringVar(value="1.0")
        delay_entry = ttk.Entry(delay_frame, textvariable=delay_duration, width=10)
        delay_entry.grid(row=0, column=1, padx=5)
        
        # 根据步骤类型显示/隐藏相应框架
        def show_hide_frames():
            if step_type.get() == Strings.MOUSE:
                mouse_frame.pack(pady=10)
                keyboard_frame.pack_forget()
                delay_frame.pack_forget()
            elif step_type.get() == Strings.KEYBOARD:
                keyboard_frame.pack(pady=10)
                mouse_frame.pack_forget()
                delay_frame.pack_forget()
            else:  # 延时步骤
                delay_frame.pack(pady=10)
                mouse_frame.pack_forget()
                keyboard_frame.pack_forget()
        
        show_hide_frames()
        type_combobox.bind("<<ComboboxSelected>>", lambda e: show_hide_frames())
        
        def add_step():
            if step_type.get() == Strings.MOUSE:
                # 映射按钮文本到值
                button_map = {Strings.LEFT: "left", Strings.RIGHT: "right", Strings.MIDDLE: "middle"}
                action_map = {Strings.CLICK: "click", Strings.PRESS: "press", Strings.RELEASE: "release"}
                
                self.step_manager.add_step({
                    "type": "mouse",
                    "button": button_map[mouse_button.get()],
                    "action": action_map[mouse_action.get()]
                })
            elif step_type.get() == Strings.KEYBOARD:
                action_map = {Strings.PRESS: "press", Strings.RELEASE: "release"}
                
                self.step_manager.add_step({
                    "type": "keyboard",
                    "key": keyboard_key.get(),
                    "action": action_map[keyboard_action.get()]
                })
            else:  # 延时步骤
                try:
                    duration = float(delay_duration.get())
                    if duration <= 0:
                        messagebox.showerror("错误", "延时时间必须大于0")
                        return
                    
                    self.step_manager.add_step({
                        "type": "delay",
                        "duration": duration
                    })
                except ValueError:
                    messagebox.showerror("错误", "请输入有效的数字")
                    return
            
            self.update_steps_tree()
            window.destroy()
        
        # 按钮框架
        button_frame = ttk.Frame(window)
        button_frame.pack(pady=10)
        
        add_btn = ttk.Button(button_frame, text=Strings.CONFIRM, command=add_step)
        add_btn.grid(row=0, column=0, padx=5)
        
        cancel_btn = ttk.Button(button_frame, text=Strings.CANCEL, command=window.destroy)
        cancel_btn.grid(row=0, column=1, padx=5)
    
    def edit_step_event(self, event):
        """处理步骤树形视图的双击事件"""
        selection = self.steps_tree.selection()
        if selection:
            self.edit_step()
    
    def edit_step(self):
        """编辑选中的步骤"""
        selection = self.steps_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个要编辑的步骤")
            return
        
        index = self.steps_tree.index(selection[0])
        step = self.step_manager.get_step(index)
        if not step:
            messagebox.showerror("错误", "无法获取步骤信息")
            return
        
        window = tk.Toplevel(self.root)
        window.title(Strings.EDIT_STEP)
        window.geometry("300x300")
        window.resizable(False, False)
        
        # 步骤类型选择
        type_label = ttk.Label(window, text=Strings.STEP_TYPE)
        type_label.pack(pady=5)
        
        step_type = tk.StringVar(value=step["type"])
        type_combobox = ttk.Combobox(window, textvariable=step_type, 
                                    values=["mouse", "keyboard", "delay"], 
                                    state="readonly")
        type_combobox.pack(pady=5)
        
        # 鼠标步骤框架
        mouse_frame = ttk.Frame(window)
        
        mouse_button_label = ttk.Label(mouse_frame, text=Strings.MOUSE_BUTTON)
        mouse_button_label.grid(row=0, column=0, padx=5)
        
        # 映射按钮值到文本
        button_reverse_map = {"left": Strings.LEFT, "right": Strings.RIGHT, "middle": Strings.MIDDLE}
        mouse_button = tk.StringVar(value=button_reverse_map.get(step.get("button", "left"), Strings.LEFT))
        mouse_combobox = ttk.Combobox(mouse_frame, textvariable=mouse_button, 
                                     values=[Strings.LEFT, Strings.RIGHT, Strings.MIDDLE], 
                                     state="readonly")
        mouse_combobox.grid(row=0, column=1, padx=5)
        
        mouse_action_label = ttk.Label(mouse_frame, text=Strings.ACTION)
        mouse_action_label.grid(row=1, column=0, padx=5)
        
        # 映射动作值到文本
        action_reverse_map = {"click": Strings.CLICK, "press": Strings.PRESS, "release": Strings.RELEASE}
        mouse_action = tk.StringVar(value=action_reverse_map.get(step.get("action", "click"), Strings.CLICK))
        mouse_action_combobox = ttk.Combobox(mouse_frame, textvariable=mouse_action, 
                                            values=[Strings.CLICK, Strings.PRESS, Strings.RELEASE], 
                                            state="readonly")
        mouse_action_combobox.grid(row=1, column=1, padx=5)
        
        # 键盘步骤框架
        keyboard_frame = ttk.Frame(window)
        
        keyboard_key_label = ttk.Label(keyboard_frame, text=Strings.KEY)
        keyboard_key_label.grid(row=0, column=0, padx=5)
        
        keyboard_key = tk.StringVar(value=step.get("key", "a"))
        keyboard_combobox = ttk.Combobox(keyboard_frame, textvariable=keyboard_key, 
                                        values=[
                                            "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", 
                                            "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
                                            "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
                                            "esc", "enter", "space", "tab", "shift", "ctrl", "alt"
                                        ], state="readonly")
        keyboard_combobox.grid(row=0, column=1, padx=5)
        
        keyboard_action_label = ttk.Label(keyboard_frame, text=Strings.ACTION)
        keyboard_action_label.grid(row=1, column=0, padx=5)
        
        keyboard_action = tk.StringVar(value=action_reverse_map.get(step.get("action", "press"), Strings.PRESS))
        keyboard_action_combobox = ttk.Combobox(keyboard_frame, textvariable=keyboard_action, 
                                               values=[Strings.PRESS, Strings.RELEASE], 
                                               state="readonly")
        keyboard_action_combobox.grid(row=1, column=1, padx=5)
        
        # 延时步骤框架
        delay_frame = ttk.Frame(window)
        
        delay_label = ttk.Label(delay_frame, text=Strings.DELAY)
        delay_label.grid(row=0, column=0, padx=5)
        
        delay_duration = tk.StringVar(value=str(step.get("duration", 1.0)))
        delay_entry = ttk.Entry(delay_frame, textvariable=delay_duration, width=10)
        delay_entry.grid(row=0, column=1, padx=5)
        
        # 根据步骤类型显示/隐藏相应框架
        def show_hide_frames():
            if step_type.get() == "mouse":
                mouse_frame.pack(pady=10)
                keyboard_frame.pack_forget()
                delay_frame.pack_forget()
            elif step_type.get() == "keyboard":
                keyboard_frame.pack(pady=10)
                mouse_frame.pack_forget()
                delay_frame.pack_forget()
            else:  # 延时步骤
                delay_frame.pack(pady=10)
                mouse_frame.pack_forget()
                keyboard_frame.pack_forget()
        
        show_hide_frames()
        type_combobox.bind("<<ComboboxSelected>>", lambda e: show_hide_frames())
        
        def update_step():
            if step_type.get() == "mouse":
                # 映射按钮文本到值
                button_map = {Strings.LEFT: "left", Strings.RIGHT: "right", Strings.MIDDLE: "middle"}
                action_map = {Strings.CLICK: "click", Strings.PRESS: "press", Strings.RELEASE: "release"}
                
                updated_step = {
                    "type": "mouse",
                    "button": button_map[mouse_button.get()],
                    "action": action_map[mouse_action.get()]
                }
            elif step_type.get() == "keyboard":
                action_map = {Strings.PRESS: "press", Strings.RELEASE: "release"}
                
                updated_step = {
                    "type": "keyboard",
                    "key": keyboard_key.get(),
                    "action": action_map[keyboard_action.get()]
                }
            else:  # 延时步骤
                try:
                    duration = float(delay_duration.get())
                    if duration <= 0:
                        messagebox.showerror("错误", "延时时间必须大于0")
                        return
                    
                    updated_step = {
                        "type": "delay",
                        "duration": duration
                    }
                except ValueError:
                    messagebox.showerror("错误", "请输入有效的数字")
                    return
            
            if self.step_manager.update_step(index, updated_step):
                self.update_steps_tree()
                window.destroy()
            else:
                messagebox.showerror("错误", "更新步骤失败")
        
        # 按钮框架
        button_frame = ttk.Frame(window)
        button_frame.pack(pady=10)
        
        update_btn = ttk.Button(button_frame, text=Strings.CONFIRM, command=update_step)
        update_btn.grid(row=0, column=0, padx=5)
        
        cancel_btn = ttk.Button(button_frame, text=Strings.CANCEL, command=window.destroy)
        cancel_btn.grid(row=0, column=1, padx=5)
    
    def remove_step(self):
        """删除选中的步骤"""
        selection = self.steps_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个要删除的步骤")
            return
        
        index = self.steps_tree.index(selection[0])
        if self.step_manager.remove_step(index) is not None:
            self.update_steps_tree()
        else:
            messagebox.showerror("错误", "删除步骤失败")
    
    def clear_steps(self):
        """清空所有步骤"""
        if messagebox.askyesno("确认", "确定要清空所有步骤吗？"):
            self.step_manager.clear()
            self.update_steps_tree()
    
    def load_config_ui(self):
        """从UI加载配置"""
        filename = filedialog.askopenfilename(
            title="选择配置文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                    self.config.update(saved_config)
                
                # 更新UI显示
                self.step_delay_var.set(str(self.config['step_delay']))
                self.loop_delay_var.set(str(self.config['loop_delay']))
                self.loop_count_var.set(str(self.config['loop_count']))
                
                # 重新设置监听器
                if hasattr(self, 'keyboard_listener') and self.keyboard_listener:
                    self.keyboard_listener.stop()
                self.setup_listeners()
                
                messagebox.showinfo("成功", "配置加载成功")
            except Exception as e:
                logger.error(f"加载配置失败: {e}")
                messagebox.showerror("错误", f"加载配置失败: {e}")
    
    def load_background(self):
        """加载背景图片"""
        filename = filedialog.askopenfilename(
            title="选择背景图片",
            filetypes=[("图片文件", "*.png;*.jpg;*.jpeg;*.gif;*.bmp"), ("所有文件", "*.*")]
        )
        if filename:
            try:
                self.config['bg_image'] = filename
                self.set_background(filename)
                messagebox.showinfo("成功", "背景图片加载成功")
            except Exception as e:
                logger.error(f"加载背景图片失败: {e}")
                messagebox.showerror("错误", f"加载背景图片失败: {e}")
    
    def remove_background(self):
        """移除背景图片"""
        self.config['bg_image'] = None
        # 移除现有背景
        if hasattr(self, 'canvas'):
            self.canvas.destroy()
        
        # 重新创建主框架
        if hasattr(self, 'main_frame'):
            self.main_frame.destroy()
        
        self.create_widgets()
        messagebox.showinfo("成功", "背景图片已移除")
    
    def set_background(self, image_path):
        """设置背景图片"""
        try:
            # 移除现有背景
            if hasattr(self, 'canvas'):
                self.canvas.destroy()
            
            if hasattr(self, 'main_frame'):
                self.main_frame.destroy()
            
            # 加载新背景
            self.bg_image = Image.open(image_path)
            
            # 调整图片大小以适应窗口
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            img_ratio = self.bg_image.width / self.bg_image.height
            screen_ratio = screen_width / screen_height
            
            if img_ratio > screen_ratio:
                new_width = min(1000, screen_width - 100)
                new_height = int(new_width / img_ratio)
            else:
                new_height = min(700, screen_height - 100)
                new_width = int(new_height * img_ratio)
            
            self.bg_image = self.bg_image.resize((new_width, new_height), Image.LANCZOS)
            self.bg_photo = ImageTk.PhotoImage(self.bg_image)
            
            # 创建画布作为背景
            self.canvas = tk.Canvas(self.root, width=new_width, height=new_height, highlightthickness=0)
            self.canvas.pack(expand=True, fill="both")
            self.canvas.create_image(new_width//2, new_height//2, image=self.bg_photo, anchor="center")
            
            # 创建主框架
            self.main_frame = tk.Frame(self.canvas, bg="#ffffff", bd=2, relief="raised")
            self.main_frame.place(relx=0.5, rely=0.5, anchor="center", width=700, height=600)
            
            # 重新创建所有控件
            self.create_widgets()
            
        except Exception as e:
            logger.error(f"设置背景图片时出错: {e}")
            messagebox.showerror("错误", f"设置背景图片时出错: {e}")
            # 恢复无背景的界面
            self.remove_background()
    
    def start_autoclicker(self):
        """开始自动连点"""
        if not self.step_manager.steps:
            messagebox.showwarning("警告", "请先添加至少一个步骤")
            return
        
        if self.is_running or self.is_counting_down:
            return
            
        self.is_counting_down = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.update_status_indicator("准备中", "orange")
        self.current_loop = 0
        
        self.thread = threading.Thread(target=self.countdown_then_start)
        self.thread.daemon = True
        self.thread.start()
    
    def countdown_then_start(self):
        """倒计时然后开始"""
        for i in range(5, 0, -1):
            if not self.is_counting_down:
                self.update_status_indicator("已取消", "green")
                return
                
            self.update_countdown(f"{i}秒后开始...")
            time.sleep(1)
        
        if self.is_counting_down:
            self.is_counting_down = False
            self.is_running = True
            self.update_status_indicator("正在使用", "red")
            self.update_countdown("")
            self.run_autoclicker()
    
    def stop_autoclicker(self):
        """停止自动连点"""
        self.is_counting_down = False
        self.is_running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.update_status_indicator("已停止", "green")
        self.update_countdown("")
        self.update_loop_count("")
    
    def run_autoclicker(self):
        """执行自动连点"""
        mouse_controller = mouse.Controller()
        keyboard_controller = keyboard.Controller()
        
        max_loops = self.config['loop_count']
        current_loop = 0
        
        while self.is_running and (max_loops == 0 or current_loop < max_loops):
            current_loop += 1
            self.current_loop = current_loop
            
            if max_loops > 0:
                self.update_loop_count(f"循环: {current_loop}/{max_loops}")
            else:
                self.update_loop_count(f"循环: {current_loop} (无限)")
            
            for step in self.step_manager.steps:
                if not self.is_running:
                    break
                
                if step["type"] == "mouse":
                    button = None
                    if step["button"] == "left":
                        button = Button.left
                    elif step["button"] == "right":
                        button = Button.right
                    elif step["button"] == "middle":
                        button = Button.middle
                    
                    if step["action"] == "click":
                        mouse_controller.click(button)
                    elif step["action"] == "press":
                        mouse_controller.press(button)
                    elif step["action"] == "release":
                        mouse_controller.release(button)
                
                elif step["type"] == "keyboard":
                    key = None
                    if step["key"] in ["esc", "enter", "space", "tab", "shift", "ctrl", "alt"]:
                        key = getattr(Key, step["key"])
                    else:
                        key = step["key"]
                    
                    if step["action"] == "press":
                        keyboard_controller.press(key)
                    elif step["action"] == "release":
                        keyboard_controller.release(key)
                
                elif step["type"] == "delay":
                    time.sleep(step["duration"])
                    continue  # 跳过步骤间隔延迟
                
                time.sleep(self.config['step_delay'])
            
            if self.is_running and (max_loops == 0 or current_loop < max_loops):
                time.sleep(self.config['loop_delay'])
        
        # 循环结束后的清理
        self.is_running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.update_status_indicator("已完成", "green")
        self.update_loop_count("")
    
    def on_key_press(self, key):
        """键盘按键事件处理"""
        if key in self.start_hotkey and not self.is_running and not self.is_counting_down:
            self.start_autoclicker()
        
        if key in self.stop_hotkeys and (self.is_running or self.is_counting_down):
            self.stop_autoclicker()
    
    def update_countdown(self, text):
        """更新倒计时显示"""
        def update():
            self.countdown_label.config(text=text)
        self.root.after(0, update)
    
    def update_loop_count(self, text):
        """更新循环计数显示"""
        def update():
            self.loop_count_label.config(text=text)
        self.root.after(0, update)

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoClicker(root)
    root.mainloop()
    
    # 清空步骤 程序关闭后清空 steps.json 文件 
    try:
        with open('steps.json', 'w', encoding='utf-8') as f:
            f.write('[]')
        print("已清空 步骤steps 文件")   
    except Exception as e:
        print(f"清空 steps.json 文件时出错: {e}")
        
    print("欢迎本次使用")
    
    