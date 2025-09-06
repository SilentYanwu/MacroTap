import time
import threading
from pynput import mouse, keyboard
from pynput.mouse import Button
from pynput.keyboard import Key, KeyCode, Listener
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import os

class AutoClicker:
    def __init__(self, root):
        self.root = root
        self.root.title("自定义连点器")
        self.root.geometry("800x600")
        self.root.resizable(False, False)
        
        # 设置窗口透明度
        self.root.attributes('-alpha', 0.9)
        
        # 加载背景图片
        self.set_background("bg.png")
        
        # 步骤列表
        self.steps = []
        self.current_step = 0
        self.is_running = False
        self.is_counting_down = False
        self.thread = None
        
        # 间隔时间设置
        self.step_delay = 0.5
        self.loop_delay = 0.5
        
        # 快捷键设置
        self.start_hotkey = {KeyCode.from_char('f')}
        self.stop_hotkeys = {KeyCode.from_char('q')}
        
        # 创建界面
        self.create_widgets()
        
        # 启动键盘监听器
        self.keyboard_listener = Listener(on_press=self.on_key_press)
        self.keyboard_listener.daemon = True
        self.keyboard_listener.start()
        
        # 添加默认步骤
        self.add_default_steps()
        
        # 初始化状态指示器
        self.update_status_indicator("尚未使用", "green")
    
    def set_background(self, image_path):
        try:
            if os.path.exists(image_path):
                self.bg_image = Image.open(image_path)
                
                # 调整图片大小以适应窗口
                # 获取用户显示器的分辨率
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
                self.main_frame.place(relx=0.5, rely=0.5, anchor="center", width=500)
                
                # 设置主框架透明度
                self.main_frame.configure(bg=self._from_rgb((240, 240, 240, 200)))
            else:
                self.main_frame = tk.Frame(self.root, bg="#f0f0f0", bd=2, relief="raised")
                self.main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        except Exception as e:
            print(f"设置背景图片时出错: {e}")
            self.main_frame = tk.Frame(self.root, bg="#f0f0f0", bd=2, relief="raised")
            self.main_frame.pack(expand=True, fill="both", padx=20, pady=20)
    
    # RGB转为为颜色代码
    def _from_rgb(self, rgb):
        return "#%02x%02x%02x" % rgb[:3]
    
    def create_widgets(self):
        # 状态指示器
        self.status_indicator = tk.Frame(self.main_frame, height=30, bg="green")
        self.status_indicator.pack(fill="x", pady=5)
        
        self.status_text = tk.Label(
            self.status_indicator, 
            text="状态: 尚未使用", 
            bg="green", 
            fg="white", 
            font=("微软雅黑", 12, "bold")
        )
        self.status_text.pack(expand=True)
        
        # 标题
        title_label = ttk.Label(self.main_frame, text="多步骤连点器", font=("微软雅黑", 16, "bold"))
        title_label.pack(pady=10)
        
        # 说明
        desc_label = ttk.Label(self.main_frame, 
                              text="快捷键: F键开始 | Q键停止\n开始后有5秒延迟时间，请切换到目标窗口",
                              font=("微软雅黑", 10), justify=tk.CENTER)
        desc_label.pack(pady=5)
        
        # 间隔时间设置框架
        delay_frame = ttk.LabelFrame(self.main_frame, text="间隔时间设置")
        delay_frame.pack(pady=10, padx=20, fill="x")
        
        # 步骤间隔设置
        step_delay_frame = ttk.Frame(delay_frame)
        step_delay_frame.pack(pady=5, fill="x", padx=10)
        
        step_delay_label = ttk.Label(step_delay_frame, text="步骤间隔(秒):")
        step_delay_label.grid(row=0, column=0, padx=5, sticky="w")
        
        self.step_delay_var = tk.StringVar(value="0.5")
        step_delay_entry = ttk.Entry(step_delay_frame, textvariable=self.step_delay_var, width=10)
        step_delay_entry.grid(row=0, column=1, padx=5)
        
        set_step_delay_btn = ttk.Button(step_delay_frame, text="设置", command=self.set_step_delay)
        set_step_delay_btn.grid(row=0, column=2, padx=5)
        
        # 循环间隔设置
        loop_delay_frame = ttk.Frame(delay_frame)
        loop_delay_frame.pack(pady=5, fill="x", padx=10)
        
        loop_delay_label = ttk.Label(loop_delay_frame, text="循环间隔(秒):")
        loop_delay_label.grid(row=0, column=0, padx=5, sticky="w")
        
        self.loop_delay_var = tk.StringVar(value="0.5")
        loop_delay_entry = ttk.Entry(loop_delay_frame, textvariable=self.loop_delay_var, width=10)
        loop_delay_entry.grid(row=0, column=1, padx=5)
        
        set_loop_delay_btn = ttk.Button(loop_delay_frame, text="设置", command=self.set_loop_delay)
        set_loop_delay_btn.grid(row=0, column=2, padx=5)
        
        # 步骤框架
        steps_frame = ttk.LabelFrame(self.main_frame, text="步骤列表")
        steps_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        # 步骤列表
        self.steps_listbox = tk.Listbox(steps_frame, height=6, font=("微软雅黑", 9))
        self.steps_listbox.pack(pady=10, padx=10, fill="both", expand=True)
        
        # 按钮框架
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(pady=10)
        
        # 添加步骤按钮
        add_step_btn = ttk.Button(button_frame, text="添加步骤", command=self.add_step_window)
        add_step_btn.grid(row=0, column=0, padx=5)
        
        # 删除步骤按钮
        remove_step_btn = ttk.Button(button_frame, text="删除步骤", command=self.remove_step)
        remove_step_btn.grid(row=0, column=1, padx=5)
        
        # 清空步骤按钮
        clear_steps_btn = ttk.Button(button_frame, text="清空步骤", command=self.clear_steps)
        clear_steps_btn.grid(row=0, column=2, padx=5)
        
        # 控制按钮框架
        control_frame = ttk.Frame(self.main_frame)
        control_frame.pack(pady=10)
        
        # 开始按钮
        self.start_btn = ttk.Button(control_frame, text="开始 (F)", command=self.start_autoclicker)
        self.start_btn.grid(row=0, column=0, padx=5)
        
        # 停止按钮
        self.stop_btn = ttk.Button(control_frame, text="停止 (Q)", command=self.stop_autoclicker, state="disabled")
        self.stop_btn.grid(row=0, column=1, padx=5)
        
        # 倒计时标签
        self.countdown_label = ttk.Label(self.main_frame, text="", font=("微软雅黑", 12, "bold"), foreground="blue")
        self.countdown_label.pack(pady=5)
    
    def set_step_delay(self):
        try:
            delay = float(self.step_delay_var.get())
            if delay < 0:
                messagebox.showerror("错误", "延迟时间不能为负数")
                return
            self.step_delay = delay
            messagebox.showinfo("成功", f"步骤间延迟已设置为 {delay} 秒")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
    
    def set_loop_delay(self):
        try:
            delay = float(self.loop_delay_var.get())
            if delay < 0:
                messagebox.showerror("错误", "延迟时间不能为负数")
                return
            self.loop_delay = delay
            messagebox.showinfo("成功", f"循环间延迟已设置为 {delay} 秒")
        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")
            
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
        self.steps.append({"type": "mouse", "button": "right", "action": "click"})
        self.steps.append({"type": "keyboard", "key": "esc", "action": "press"})
        self.steps.append({"type": "mouse", "button": "left", "action": "click"})
        
        self.update_steps_listbox()
    
    def update_steps_listbox(self):
        self.steps_listbox.delete(0, tk.END)
        for i, step in enumerate(self.steps):
            if step["type"] == "mouse":
                self.steps_listbox.insert(tk.END, f"步骤 {i+1}: 鼠标 {step['button']}键 {step['action']}")
            else:
                self.steps_listbox.insert(tk.END, f"步骤 {i+1}: 键盘 {step['key']}键 {step['action']}")
    
    def add_step_window(self):
        window = tk.Toplevel(self.root)
        window.title("添加步骤")
        window.geometry("300x250")
        window.resizable(False, False)
        
        type_label = ttk.Label(window, text="步骤类型:")
        type_label.pack(pady=5)
        
        step_type = tk.StringVar(value="mouse")
        type_combobox = ttk.Combobox(window, textvariable=step_type, values=["mouse", "keyboard"], state="readonly")
        type_combobox.pack(pady=5)
        
        mouse_frame = ttk.Frame(window)
        
        mouse_button_label = ttk.Label(mouse_frame, text="鼠标按钮:")
        mouse_button_label.grid(row=0, column=0, padx=5)
        
        mouse_button = tk.StringVar(value="left")
        mouse_combobox = ttk.Combobox(mouse_frame, textvariable=mouse_button, values=["left", "right", "middle"], state="readonly")
        mouse_combobox.grid(row=0, column=1, padx=5)
        
        mouse_action_label = ttk.Label(mouse_frame, text="动作:")
        mouse_action_label.grid(row=1, column=0, padx=5)
        
        mouse_action = tk.StringVar(value="click")
        mouse_action_combobox = ttk.Combobox(mouse_frame, textvariable=mouse_action, values=["click", "press", "release"], state="readonly")
        mouse_action_combobox.grid(row=1, column=1, padx=5)
        
        keyboard_frame = ttk.Frame(window)
        
        keyboard_key_label = ttk.Label(keyboard_frame, text="按键:")
        keyboard_key_label.grid(row=0, column=0, padx=5)
        
        keyboard_key = tk.StringVar(value="a")
        keyboard_combobox = ttk.Combobox(keyboard_frame, textvariable=keyboard_key, values=[
            "a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k", "l", "m", 
            "n", "o", "p", "q", "r", "s", "t", "u", "v", "w", "x", "y", "z",
            "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
            "esc", "enter", "space", "tab", "shift", "ctrl", "alt"
        ], state="readonly")
        keyboard_combobox.grid(row=0, column=1, padx=5)
        
        keyboard_action_label = ttk.Label(keyboard_frame, text="动作:")
        keyboard_action_label.grid(row=1, column=0, padx=5)
        
        keyboard_action = tk.StringVar(value="press")
        keyboard_action_combobox = ttk.Combobox(keyboard_frame, textvariable=keyboard_action, values=["press", "release"], state="readonly")
        keyboard_action_combobox.grid(row=1, column=1, padx=5)
        
        def show_hide_frames():
            if step_type.get() == "mouse":
                mouse_frame.pack(pady=10)
                keyboard_frame.pack_forget()
            else:
                keyboard_frame.pack(pady=10)
                mouse_frame.pack_forget()
        
        show_hide_frames()
        type_combobox.bind("<<ComboboxSelected>>", lambda e: show_hide_frames())
        
        def add_step():
            if step_type.get() == "mouse":
                self.steps.append({
                    "type": "mouse",
                    "button": mouse_button.get(),
                    "action": mouse_action.get()
                })
            else:
                self.steps.append({
                    "type": "keyboard",
                    "key": keyboard_key.get(),
                    "action": keyboard_action.get()
                })
            
            self.update_steps_listbox()
            window.destroy()
        
        add_btn = ttk.Button(window, text="添加", command=add_step)
        add_btn.pack(pady=10)
    
    def remove_step(self):
        selection = self.steps_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请先选择一个要删除的步骤")
            return
        
        index = selection[0]
        self.steps.pop(index)
        self.update_steps_listbox()
    
    def clear_steps(self):
        self.steps.clear()
        self.update_steps_listbox()
    
    def start_autoclicker(self):
        if not self.steps:
            messagebox.showwarning("警告", "请先添加至少一个步骤")
            return
        
        if self.is_running or self.is_counting_down:
            return
            
        self.is_counting_down = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.update_status_indicator("准备中", "orange")
        
        self.thread = threading.Thread(target=self.countdown_then_start)
        self.thread.daemon = True
        self.thread.start()
    
    def countdown_then_start(self):
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
        self.is_counting_down = False
        self.is_running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.update_status_indicator("已停止", "green")
        self.update_countdown("")
    
    def run_autoclicker(self):
        mouse_controller = mouse.Controller()
        keyboard_controller = keyboard.Controller()
        
        while self.is_running:
            for step in self.steps:
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
                
                else:
                    key = None
                    if step["key"] in ["esc", "enter", "space", "tab", "shift", "ctrl", "alt"]:
                        key = getattr(Key, step["key"])
                    else:
                        key = step["key"]
                    
                    if step["action"] == "press":
                        keyboard_controller.press(key)
                    elif step["action"] == "release":
                        keyboard_controller.release(key)
                
                time.sleep(self.step_delay)
            
            time.sleep(self.loop_delay)
    
    def on_key_press(self, key):
        if key in self.start_hotkey and not self.is_running and not self.is_counting_down:
            self.start_autoclicker()
        
        if key in self.stop_hotkeys and (self.is_running or self.is_counting_down):
            self.stop_autoclicker()
    
    def update_countdown(self, text):
        def update():
            self.countdown_label.config(text=text)
        self.root.after(0, update)

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoClicker(root)
    root.mainloop()