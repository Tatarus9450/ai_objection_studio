import cv2
import time
import csv
import platform
from datetime import datetime
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image
from ultralytics import YOLO
from collections import Counter

class ObjectDetectionApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI Vision Pro - Object Detection Suite")
        self.geometry("1400x850")
        self.minsize(1100, 700)
        
        # Core Variables
        self.model = None
        self.current_model_name = ""
        
        # Media & State Variables
        self.cap = None
        self.is_running = False
        self.is_recording = False
        self.video_writer = None
        self.source_type = ctk.StringVar(value="Webcam")
        self.source_path = ctk.StringVar(value="0")
        self.current_frame = None
        self.current_annotated_frame = None
        
        # Performance Tracking
        self.fps_start_time = 0
        self.fps_frames_count = 0
        self.current_fps = 0
        
        # CSV Logging
        self.csv_file = None
        self.csv_writer = None
        self.log_to_csv_var = ctk.BooleanVar(value=False)

        # App location (portable across OS and launch locations)
        self.app_dir = Path(__file__).resolve().parent
        self.model_dir = self.app_dir / "model"
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.available_models_map = {}
        
        # Directories
        self.capture_dir = self.app_dir / "captures"
        self.capture_dir.mkdir(parents=True, exist_ok=True)
            
        self.csv_dir = self.app_dir / "csv_logs"
        self.csv_dir.mkdir(parents=True, exist_ok=True)
            
        # Build UI Structure
        self.setup_ui()
        self.refresh_models()
        self.update_source_inputs()

    def get_available_models(self):
        model_paths = []
        for pattern in ("*.pt", "*.engine"):
            model_paths.extend(self.model_dir.glob(pattern))

        models = sorted({path.name for path in model_paths})
        if not models:
            models = ["yolov8n.pt"]
        return models

    def setup_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0) # Info panel
        
        # ==========================================
        # 1. SIDEBAR
        # ==========================================
        self.sidebar_frame = ctk.CTkFrame(self, width=320, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(2, weight=1)
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="AI Vision Pro 🚀", font=ctk.CTkFont(size=26, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.status_label = ctk.CTkLabel(self.sidebar_frame, text="Status: Ready", text_color="gray", font=ctk.CTkFont(size=14))
        self.status_label.grid(row=1, column=0, padx=20, pady=(0, 20))
        
        # --- TABVIEW ---
        self.tabview = ctk.CTkTabview(self.sidebar_frame, width=300)
        self.tabview.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
        self.tabview.add("Main")
        self.tabview.add("Settings")
        
        # ---- MAIN TAB ----
        # Model Selection
        ctk.CTkLabel(self.tabview.tab("Main"), text="Model Selection:", anchor="w", font=ctk.CTkFont(weight="bold")).pack(fill="x", padx=10, pady=(10, 0))
        self.model_var = ctk.StringVar()
        self.model_dropdown = ctk.CTkOptionMenu(self.tabview.tab("Main"), variable=self.model_var, values=["yolov8n.pt"])
        self.model_dropdown.pack(fill="x", padx=10, pady=(5, 5))
        self.refresh_btn = ctk.CTkButton(self.tabview.tab("Main"), text="↻ Refresh Models", command=self.refresh_models, fg_color="transparent", border_width=1, text_color=("gray10", "#DCE4EE"))
        self.refresh_btn.pack(fill="x", padx=10, pady=(0, 15))
        
        # Source Selection
        ctk.CTkLabel(self.tabview.tab("Main"), text="Input Source:", anchor="w", font=ctk.CTkFont(weight="bold")).pack(fill="x", padx=10, pady=(10, 0))
        self.source_dropdown = ctk.CTkOptionMenu(self.tabview.tab("Main"), variable=self.source_type, values=["Webcam", "Video File", "Image File"], command=self.update_source_inputs)
        self.source_dropdown.pack(fill="x", padx=10, pady=(5, 10))
        
        self.source_entry = ctk.CTkEntry(self.tabview.tab("Main"), textvariable=self.source_path)
        self.source_entry.pack(fill="x", padx=10, pady=(0, 5))
        
        self.browse_btn = ctk.CTkButton(self.tabview.tab("Main"), text="Browse File", command=self.browse_file)
        self.browse_btn.pack(fill="x", padx=10, pady=(0, 20))
        
        # Start/Stop Controls
        self.start_btn = ctk.CTkButton(self.tabview.tab("Main"), text="▶ Start Detection", command=self.start_detection, fg_color="#2FA572", hover_color="#1F7A52", height=40, font=ctk.CTkFont(weight="bold", size=15))
        self.start_btn.pack(fill="x", padx=10, pady=(20, 10))
        
        self.stop_btn = ctk.CTkButton(self.tabview.tab("Main"), text="⏹ Stop Detection", command=self.stop_detection, fg_color="#E04F5F", hover_color="#A83A46", height=40, state="disabled", font=ctk.CTkFont(weight="bold", size=15))
        self.stop_btn.pack(fill="x", padx=10, pady=(0, 10))

        # ---- SETTINGS TAB ----
        # Confidence
        ctk.CTkLabel(self.tabview.tab("Settings"), text="Confidence Threshold", anchor="w", font=ctk.CTkFont(weight="bold")).pack(fill="x", padx=10, pady=(15, 0))
        self.conf_val_label = ctk.CTkLabel(self.tabview.tab("Settings"), text="0.25", text_color="gray")
        self.conf_val_label.pack(anchor="e", padx=10)
        self.conf_slider = ctk.CTkSlider(self.tabview.tab("Settings"), from_=0.01, to=1.0, command=self.update_conf_label)
        self.conf_slider.set(0.25)
        self.conf_slider.pack(fill="x", padx=10, pady=(0, 10))
        
        # IoU
        ctk.CTkLabel(self.tabview.tab("Settings"), text="IoU Threshold (NMS)", anchor="w", font=ctk.CTkFont(weight="bold")).pack(fill="x", padx=10, pady=(10, 0))
        self.iou_val_label = ctk.CTkLabel(self.tabview.tab("Settings"), text="0.45", text_color="gray")
        self.iou_val_label.pack(anchor="e", padx=10)
        self.iou_slider = ctk.CTkSlider(self.tabview.tab("Settings"), from_=0.01, to=1.0, command=self.update_iou_label)
        self.iou_slider.set(0.45)
        self.iou_slider.pack(fill="x", padx=10, pady=(0, 10))
        
        # Resolution limit
        ctk.CTkLabel(self.tabview.tab("Settings"), text="Inference Resolution:", anchor="w", font=ctk.CTkFont(weight="bold")).pack(fill="x", padx=10, pady=(10, 0))
        self.reso_var = ctk.StringVar(value="640")
        self.reso_dropdown = ctk.CTkOptionMenu(self.tabview.tab("Settings"), variable=self.reso_var, values=["320", "640", "1280", "Native"])
        self.reso_dropdown.pack(fill="x", padx=10, pady=(5, 10))
        
        # Class Filter
        ctk.CTkLabel(self.tabview.tab("Settings"), text="Filter Classes (Comma-separated IDs):", anchor="w", font=ctk.CTkFont(weight="bold")).pack(fill="x", padx=10, pady=(10, 0))
        self.class_filter_entry = ctk.CTkEntry(self.tabview.tab("Settings"), placeholder_text="e.g. 0,1,2 (empty=all)")
        self.class_filter_entry.pack(fill="x", padx=10, pady=(5, 10))

        # CSV Logging toggle
        self.log_switch = ctk.CTkSwitch(self.tabview.tab("Settings"), text="Enable CSV Logging", variable=self.log_to_csv_var)
        self.log_switch.pack(fill="x", padx=10, pady=(10, 10))
        
        # Appearance
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["System", "Light", "Dark"], command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=4, column=0, padx=20, pady=(10, 20), sticky="ew")
        
        # ==========================================
        # 2. MAIN FRAME (Video Display)
        # ==========================================
        self.main_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Top Stats Bar
        self.stats_frame = ctk.CTkFrame(self.main_frame, height=40, fg_color="transparent")
        self.stats_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.fps_label = ctk.CTkLabel(self.stats_frame, text="FPS: 0", font=ctk.CTkFont(size=18, weight="bold"), text_color="#3B8ED0")
        self.fps_label.pack(side="left", padx=20)
        
        self.resolution_label = ctk.CTkLabel(self.stats_frame, text="Resolution: -", font=ctk.CTkFont(size=14), text_color="gray")
        self.resolution_label.pack(side="right", padx=20)
        
        # Video Label (Dynamic sizing)
        self.video_bg = ctk.CTkFrame(self.main_frame, corner_radius=10)
        self.video_bg.grid(row=1, column=0, sticky="nsew")
        self.video_bg.grid_rowconfigure(0, weight=1)
        self.video_bg.grid_columnconfigure(0, weight=1)
        
        self.video_label = ctk.CTkLabel(self.video_bg, text="No Media Loaded", font=ctk.CTkFont(size=24), text_color="gray")
        self.video_label.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Bottom Action Bar
        self.action_frame = ctk.CTkFrame(self.main_frame, height=60, fg_color="transparent")
        self.action_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        self.action_frame.grid_columnconfigure((0,1), weight=1)
        
        self.snapshot_btn = ctk.CTkButton(self.action_frame, text="📸 Take Snapshot", command=self.take_snapshot, state="disabled", height=40)
        self.snapshot_btn.grid(row=0, column=0, padx=10, sticky="ew")
        
        self.record_btn = ctk.CTkButton(self.action_frame, text="⏺ Start Recording", command=self.toggle_recording, state="disabled", fg_color="#3B8ED0", hover_color="#2C6D9E", height=40)
        self.record_btn.grid(row=0, column=1, padx=10, sticky="ew")
        
        # ==========================================
        # 3. INFO PANEL (Right Side)
        # ==========================================
        self.info_frame = ctk.CTkFrame(self, width=250, corner_radius=10)
        self.info_frame.grid(row=0, column=2, padx=(0, 10), pady=10, sticky="nsew")
        self.info_frame.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(self.info_frame, text="Detection Summary", font=ctk.CTkFont(size=18, weight="bold")).grid(row=0, column=0, pady=15, padx=10)
        
        self.summary_textbox = ctk.CTkTextbox(self.info_frame, width=230, font=ctk.CTkFont(size=14))
        self.summary_textbox.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.summary_textbox.insert("0.0", "Waiting for detection...\n")
        self.summary_textbox.configure(state="disabled")

    # ==========================================
    # UI Interactions & Updates
    # ==========================================
    def update_conf_label(self, val):
        self.conf_val_label.configure(text=f"{val:.2f}")

    def update_iou_label(self, val):
        self.iou_val_label.configure(text=f"{val:.2f}")

    def change_appearance_mode_event(self, new_appearance_mode: str):
        ctk.set_appearance_mode(new_appearance_mode)
        
    def refresh_models(self):
        models = self.get_available_models()
        self.available_models_map = {model_name: str(self.model_dir / model_name) for model_name in models if (self.model_dir / model_name).is_file()}
        self.model_dropdown.configure(values=models)
        if self.model_var.get() not in models:
            self.model_var.set(models[0])

    def resolve_media_path(self, raw_path):
        candidate = Path(raw_path).expanduser()
        candidates = [candidate]
        if not candidate.is_absolute():
            candidates.append(self.app_dir / candidate)

        for path in candidates:
            if path.is_file():
                return str(path.resolve())
        return None

    def open_video_capture(self, source, is_webcam=False):
        if not is_webcam:
            return cv2.VideoCapture(source)

        backends = [None]
        system_name = platform.system()
        if system_name == "Windows":
            backends.extend([cv2.CAP_DSHOW, cv2.CAP_MSMF])
        elif system_name == "Darwin":
            backends.append(cv2.CAP_AVFOUNDATION)
        elif system_name == "Linux":
            backends.append(cv2.CAP_V4L2)

        for backend in backends:
            cap = cv2.VideoCapture(source) if backend is None else cv2.VideoCapture(source, backend)
            if cap.isOpened():
                return cap
            cap.release()

        return cv2.VideoCapture(source)

    def update_source_inputs(self, event=None):
        src = self.source_type.get()
        if src == "Webcam":
            self.source_path.set("0") # Default camera
            self.browse_btn.configure(state="disabled")
        else:
            self.source_path.set("")
            self.browse_btn.configure(state="normal")
            
    def browse_file(self):
        src = self.source_type.get()
        filetypes = []
        if src == "Video File":
            filetypes = [("Video Files", "*.mp4 *.avi *.mov *.mkv")]
        elif src == "Image File":
            filetypes = [("Image Files", "*.jpg *.jpeg *.png *.bmp")]
            
        file_path = filedialog.askopenfilename(title=f"Select {src}", filetypes=filetypes, initialdir=str(self.app_dir))
        if file_path:
            self.source_path.set(file_path)

    def load_model(self):
        selected_model = self.model_var.get()
        model_source = self.available_models_map.get(selected_model, selected_model)

        if self.current_model_name != model_source or self.model is None:
            self.status_label.configure(text=f"Loading model...", text_color="#FFA500")
            self.update() 
            try:
                self.model = YOLO(model_source)
                self.current_model_name = model_source
            except Exception as e:
                messagebox.showerror("Model Error", f"Failed to load model:\n{e}")
                raise e

    def _get_inference_kwargs(self):
        """Build dictionary of kwargs for model inference based on UI settings"""
        conf_thresh = self.conf_slider.get()
        iou_thresh = self.iou_slider.get()
        reso = self.reso_var.get()
        
        classes_str = self.class_filter_entry.get().strip()
        filter_classes = None
        if classes_str:
            try:
                filter_classes = [int(c.strip()) for c in classes_str.split(',') if c.strip().isdigit()]
            except: 
                pass
                
        kwargs = {
            "conf": conf_thresh,
            "iou": iou_thresh,
            "verbose": False
        }
        
        if filter_classes:
            kwargs["classes"] = filter_classes
            
        if reso != "Native":
            kwargs["imgsz"] = int(reso)
            
        return kwargs

    def update_summary(self, results):
        self.summary_textbox.configure(state="normal")
        self.summary_textbox.delete("0.0", "end")
        
        detail_str = []
        
        if not results or len(results[0].boxes) == 0:
            self.summary_textbox.insert("0.0", "No objects detected.\n")
            self.summary_textbox.configure(state="disabled")
            if self.csv_file and not self.csv_file.closed:
                self.csv_writer.writerow([datetime.now().strftime("%H:%M:%S.%f")[:-3], 0, ""])
            return
            
        # Extract class indices and names
        boxes = results[0].boxes
        names = self.model.names
        class_ids = boxes.cls.cpu().numpy().astype(int)
        
        # Count occurrences
        counts = Counter(class_ids)
        total_objects = len(class_ids)
        
        summary_text = f"Total Detected: {total_objects}\n"
        summary_text += "-"*20 + "\n"
        
        for class_id, count in counts.items():
            class_name = names[class_id]
            summary_text += f"• {class_name.capitalize()}: {count}\n"
            detail_str.append(f"{class_name}:{count}")
            
        self.summary_textbox.insert("0.0", summary_text)
        self.summary_textbox.configure(state="disabled")

        if self.csv_file and not self.csv_file.closed:
            self.csv_writer.writerow([datetime.now().strftime("%H:%M:%S.%f")[:-3], total_objects, ", ".join(detail_str)])

    def toggle_recording(self):
        if not self.is_recording:
            # Start Recording
            if self.current_annotated_frame is None:
                return
            h, w = self.current_annotated_frame.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.capture_dir / f"record_{timestamp}.mp4"
            try:
                self.video_writer = cv2.VideoWriter(str(filename), fourcc, 20.0, (w, h))
                self.is_recording = True
                self.record_btn.configure(text="⏹ Stop Recording", fg_color="#E04F5F", hover_color="#A83A46")
                self.status_label.configure(text="Status: Recording...", text_color="#E04F5F")
            except Exception as e:
                messagebox.showerror("Recording Error", str(e))
        else:
            # Stop Recording
            self.is_recording = False
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            self.record_btn.configure(text="⏺ Start Recording", fg_color="#3B8ED0", hover_color="#2C6D9E")
            self.status_label.configure(text="Status: Detecting...", text_color="#2FA572")

    def take_snapshot(self):
        if self.current_annotated_frame is not None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.capture_dir / f"snapshot_{timestamp}.jpg"
            # OpenCV uses BGR, and our annotated frame is BGR natively from ultralytics plot
            cv2.imwrite(str(filename), self.current_annotated_frame)
            # Show a brief status
            self.status_label.configure(text=f"Saved snapshot!", text_color="#2FA572")

    def start_detection(self):
        try:
            self.load_model()
        except Exception:
            self.status_label.configure(text="Status: Model Error", text_color="#E04F5F")
            return

        src_type = self.source_type.get()
        src_path = self.source_path.get()
        
        # Determine if we should start CSV logging
        if self.log_to_csv_var.get():
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                csv_path = self.csv_dir / f"detect_log_{timestamp}.csv"
                self.csv_file = open(csv_path, 'w', newline='', encoding='utf-8')
                self.csv_writer = csv.writer(self.csv_file)
                self.csv_writer.writerow(["Timestamp", "Total Objects", "Details"])
            except Exception as e:
                print(f"Failed to start CSV logging: {e}")
                
        if src_type == "Image File":
            resolved_path = self.resolve_media_path(src_path)
            if not resolved_path:
                messagebox.showerror("Error", "Invalid image file path.")
                return
            self.process_image(resolved_path)
            return

        # Video / Webcam
        if src_type == "Webcam":
            try:
                src_path = int(src_path)
            except ValueError:
                messagebox.showerror("Error", "Camera index must be an integer.")
                return
        else:
            resolved_path = self.resolve_media_path(src_path)
            if not resolved_path:
                messagebox.showerror("Error", "Invalid video file path.")
                return
            src_path = resolved_path
            
        if self.cap is None or not self.cap.isOpened():
            self.cap = self.open_video_capture(src_path, is_webcam=(src_type == "Webcam"))
            
        if self.cap.isOpened():
            self.is_running = True
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.snapshot_btn.configure(state="normal")
            self.record_btn.configure(state="normal")
            self.source_dropdown.configure(state="disabled")
            self.model_dropdown.configure(state="disabled")
            self.refresh_btn.configure(state="disabled")
            self.browse_btn.configure(state="disabled")
            self.source_entry.configure(state="disabled")
            
            self.status_label.configure(text="Status: Detecting...", text_color="#2FA572")
            
            # FPS tracking initialization
            self.fps_start_time = time.time()
            self.fps_frames_count = 0
            
            self.update_frame()
        else:
            self.status_label.configure(text="Status: Media Error", text_color="#E04F5F")
            
    def stop_detection(self):
        self.is_running = False
        
        if self.is_recording:
            self.toggle_recording()
            
        if self.csv_file is not None:
            self.csv_file.close()
            self.csv_file = None
            
        if self.cap:
            self.cap.release()
            self.cap = None
            
        self.video_label.configure(image=None, text="Media stopped")
        
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.snapshot_btn.configure(state="disabled")
        self.record_btn.configure(state="disabled")
        self.source_dropdown.configure(state="normal")
        self.source_entry.configure(state="normal")
        self.model_dropdown.configure(state="normal")
        self.refresh_btn.configure(state="normal")
        self.update_source_inputs() # Re-enable browse if needed
        
        self.status_label.configure(text="Status: Stopped", text_color="gray")
        self.fps_label.configure(text="FPS: 0")

    def process_image(self, path):
        frame = cv2.imread(path)
        if frame is None:
            messagebox.showerror("Error", "Failed to read image.")
            return
            
        self.status_label.configure(text="Status: Checking Image...", text_color="#2FA572")
        self.snapshot_btn.configure(state="normal") # Enable snapshot of resulting image
        
        # Inference
        kwargs = self._get_inference_kwargs()
        results = self.model(frame, **kwargs)
            
        self.current_annotated_frame = results[0].plot()
        self.update_summary(results)
        
        self.display_frame(self.current_annotated_frame)
        self.resolution_label.configure(text=f"Resolution: {frame.shape[1]}x{frame.shape[0]}")
        self.status_label.configure(text="Status: Done", text_color="gray")
        self.fps_label.configure(text="FPS: N/A")
        
        # Re-close CSV if it was just an image (since it runs once)
        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None

    def update_frame(self):
        if self.is_running and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret and self.model is not None:
                # Update FPS
                self.fps_frames_count += 1
                elapsed = time.time() - self.fps_start_time
                if elapsed > 1.0:
                    self.current_fps = self.fps_frames_count / elapsed
                    self.fps_label.configure(text=f"FPS: {self.current_fps:.1f}")
                    self.fps_frames_count = 0
                    self.fps_start_time = time.time()
                
                # Fetch settings
                self.resolution_label.configure(text=f"Resolution: {frame.shape[1]}x{frame.shape[0]}")
                kwargs = self._get_inference_kwargs()
                
                # 1. Run YOLO detection
                results = self.model(frame, **kwargs)
                
                # 2. Draw bounding boxes
                self.current_annotated_frame = results[0].plot()
                
                # 3. Update Text Summary & CSV
                self.update_summary(results)
                
                # 4. Handle Recording
                if self.is_recording and self.video_writer is not None:
                    try:
                        self.video_writer.write(self.current_annotated_frame)
                    except Exception: pass
                
                # 5. Display
                self.display_frame(self.current_annotated_frame)
                
            else: # Video ended or error
                self.stop_detection()
                return
                
            # Request next frame ASAP
            if self.source_type.get() == "Video File":
                self.after(20, self.update_frame) 
            else:
                self.after(10, self.update_frame)

    def display_frame(self, cv_frame):
        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(cv_frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_image)
        
        # Calculate available width and height inside the main_frame
        lbl_width = self.video_bg.winfo_width()
        lbl_height = self.video_bg.winfo_height()
        
        if lbl_width > 10 and lbl_height > 10:
            # Maintain aspect ratio
            img_w, img_h = pil_image.size
            ratio = min(lbl_width/img_w, lbl_height/img_h)
            new_w = int(img_w * ratio)
            new_h = int(img_h * ratio)
            
            # Avoid ValueError on tiny resizes
            if new_w > 0 and new_h > 0:
                ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(new_w, new_h))
                self.video_label.configure(image=ctk_image, text="")
                self.video_label.image = ctk_image
        else:
            # Fallback for first initialization frames
            ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(640, 480))
            self.video_label.configure(image=ctk_image, text="")
            self.video_label.image = ctk_image

    def on_closing(self):
        self.stop_detection()
        self.destroy()

if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    
    app = ObjectDetectionApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
