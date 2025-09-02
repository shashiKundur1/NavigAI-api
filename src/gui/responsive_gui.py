"""
Responsive GUI for the AI Mock Interview System
"""

import sys
import time
import threading
import customtkinter as ctk
from tkinter import messagebox
from pathlib import Path
import logging
import queue
from datetime import datetime

# Import agent and services
from agents.mock_interview_agent import MockInterviewAgent

logger = logging.getLogger(__name__)


class ResponsiveMockInterviewGUI:
    """Responsive GUI for the AI Mock Interview System"""

    def __init__(self):
        self.agent = MockInterviewAgent()
        self.agent.gui = self

        # Initialize CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Create main window
        self.root = ctk.CTk()
        self.root.title("NavigAI - AI Mock Interview System")
        self.root.geometry("1200x800")
        self.root.minsize(800, 600)

        # Variables
        self.job_title_var = ctk.StringVar()
        self.job_description_var = ctk.StringVar()
        self.candidate_id_var = ctk.StringVar()
        self.current_question_var = ctk.StringVar()
        self.recording_time_var = ctk.StringVar(value="00:00")
        self.status_var = ctk.StringVar(value="Ready to start")

        # Animation variables
        self.pulse_animation = None
        self.pulse_size = 10
        self.pulse_growing = True
        self.spinner_animation = None
        self.spinner_angle = 0

        # Threading queue for safe GUI updates
        self.update_queue = queue.Queue()

        # Create responsive GUI
        self.create_setup_page()
        self.create_interview_page()

        # Configure grid weights for responsiveness
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Start processing update queue
        self.process_update_queue()

    def create_setup_page(self):
        """Create the setup page with job details"""
        # Setup frame with modern styling
        self.setup_frame = ctk.CTkFrame(self.root, corner_radius=15)
        self.setup_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.setup_frame.grid_rowconfigure(1, weight=1)
        self.setup_frame.grid_columnconfigure(0, weight=1)

        # Title with modern styling
        title_frame = ctk.CTkFrame(self.setup_frame, fg_color="transparent")
        title_frame.grid(row=0, column=0, pady=(0, 20))

        title_label = ctk.CTkLabel(
            title_frame,
            text="NavigAI",
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color="#1E90FF",  # DodgerBlue
        )
        title_label.pack()

        subtitle_label = ctk.CTkLabel(
            title_frame,
            text="AI Mock Interview System",
            font=ctk.CTkFont(size=16),
            text_color="#A9A9A9",  # DarkGray
        )
        subtitle_label.pack()

        # Setup form frame with modern styling
        form_frame = ctk.CTkFrame(self.setup_frame, corner_radius=10)
        form_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        form_frame.grid_columnconfigure(1, weight=1)

        # Job title with modern styling
        ctk.CTkLabel(
            form_frame, text="Job Title:", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 10))

        job_title_entry = ctk.CTkEntry(
            form_frame,
            textvariable=self.job_title_var,
            corner_radius=8,
            border_width=2,
            border_color="#1E90FF",
        )
        job_title_entry.grid(row=0, column=1, sticky="ew", padx=20, pady=(20, 10))

        # Candidate ID with modern styling
        ctk.CTkLabel(
            form_frame, text="Candidate ID:", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 10))

        candidate_id_entry = ctk.CTkEntry(
            form_frame,
            textvariable=self.candidate_id_var,
            corner_radius=8,
            border_width=2,
            border_color="#1E90FF",
        )
        candidate_id_entry.grid(row=1, column=1, sticky="ew", padx=20, pady=(0, 10))

        # Job description with modern styling
        ctk.CTkLabel(
            form_frame,
            text="Job Description:",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=2, column=0, sticky="nw", padx=20, pady=(0, 10))

        job_description_text = ctk.CTkTextbox(
            form_frame,
            height=120,
            corner_radius=8,
            border_width=2,
            border_color="#1E90FF",
        )
        job_description_text.grid(
            row=3, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 20)
        )
        form_frame.grid_rowconfigure(3, weight=1)

        # Store reference to job description text widget
        self.job_description_text = job_description_text

        # Start button with modern styling
        self.start_button = ctk.CTkButton(
            form_frame,
            text="Start Interview",
            command=self.start_interview,
            height=45,
            font=ctk.CTkFont(size=16, weight="bold"),
            corner_radius=8,
            fg_color="#1E90FF",
            hover_color="#1873CC",
        )
        self.start_button.grid(
            row=4, column=0, columnspan=2, pady=(0, 20), padx=20, sticky="ew"
        )

        # Loading frame (initially hidden)
        self.loading_frame = ctk.CTkFrame(self.root, corner_radius=15)
        self.loading_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.loading_frame.grid_rowconfigure(0, weight=1)
        self.loading_frame.grid_columnconfigure(0, weight=1)
        self.loading_frame.grid_remove()  # Hide initially

        # Loading spinner
        self.spinner_canvas = ctk.CTkCanvas(
            self.loading_frame, width=100, height=100, highlightthickness=0
        )
        self.spinner_canvas.grid(row=0, column=0, pady=20)

        # Loading text
        loading_label = ctk.CTkLabel(
            self.loading_frame,
            text="Preparing your interview...",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        loading_label.grid(row=1, column=0, pady=10)

    def create_interview_page(self):
        """Create the interview page"""
        # Interview frame (initially hidden) with modern styling
        self.interview_frame = ctk.CTkFrame(self.root, corner_radius=15)
        self.interview_frame.grid_rowconfigure(1, weight=1)
        self.interview_frame.grid_columnconfigure(0, weight=1)
        self.interview_frame.grid_remove()  # Hide initially

        # Question display with modern styling
        question_frame = ctk.CTkFrame(self.interview_frame, fg_color="transparent")
        question_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        question_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            question_frame,
            text="Current Question:",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(0, 10))

        self.question_label = ctk.CTkLabel(
            question_frame,
            text="Click 'Start Interview' to begin",
            font=ctk.CTkFont(size=16),
            wraplength=800,
            justify="left",
        )
        self.question_label.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 10))

        # AI Avatar with animation
        self.avatar_frame = ctk.CTkFrame(
            question_frame, fg_color="#1E1E1E", corner_radius=50, width=100, height=100
        )
        self.avatar_frame.grid(row=0, column=1, rowspan=2, padx=20, pady=10)

        self.avatar_canvas = ctk.CTkCanvas(
            self.avatar_frame, width=100, height=100, highlightthickness=0
        )
        self.avatar_canvas.pack(fill="both", expand=True)

        # Draw initial avatar
        self.draw_avatar()

        # Controls frame with modern styling
        controls_frame = ctk.CTkFrame(self.interview_frame, fg_color="transparent")
        controls_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)

        # Recording indicator with animation
        self.recording_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        self.recording_frame.grid(row=0, column=0, padx=10, pady=10)

        self.recording_canvas = ctk.CTkCanvas(
            self.recording_frame, width=40, height=40, highlightthickness=0
        )
        self.recording_canvas.pack()

        # Draw initial recording indicator
        self.draw_recording_indicator()

        self.recording_label = ctk.CTkLabel(
            controls_frame,
            text="Not Recording",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#A9A9A9",
        )
        self.recording_label.grid(row=0, column=1, padx=10, pady=10)

        # Recording time with modern styling
        self.time_label = ctk.CTkLabel(
            controls_frame,
            textvariable=self.recording_time_var,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#1E90FF",
        )
        self.time_label.grid(row=0, column=2, padx=20, pady=10)

        # Stop Recording button with modern styling
        self.stop_button = ctk.CTkButton(
            controls_frame,
            text="Stop Recording",
            command=self.stop_recording,
            width=150,
            height=40,
            state="disabled",
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=8,
            fg_color="#FF6347",  # Tomato
            hover_color="#E5533B",
        )
        self.stop_button.grid(row=0, column=3, padx=10, pady=10)

        # Next question button with modern styling
        self.next_button = ctk.CTkButton(
            controls_frame,
            text="Next Question",
            command=self.next_question,
            width=150,
            height=40,
            state="disabled",
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=8,
            fg_color="#1E90FF",
            hover_color="#1873CC",
        )
        self.next_button.grid(row=0, column=4, padx=10, pady=10)

        # End interview button with modern styling
        self.end_button = ctk.CTkButton(
            controls_frame,
            text="End Interview",
            command=self.end_interview,
            width=150,
            height=40,
            state="disabled",
            font=ctk.CTkFont(size=14, weight="bold"),
            corner_radius=8,
            fg_color="#FF6347",  # Tomato
            hover_color="#E5533B",
        )
        self.end_button.grid(row=0, column=5, padx=10, pady=10)

        # Status frame with modern styling
        status_frame = ctk.CTkFrame(
            self.interview_frame, fg_color="#2B2B2B", corner_radius=8
        )
        status_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=10)

        self.status_label = ctk.CTkLabel(
            status_frame,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=14),
            wraplength=800,
        )
        self.status_label.grid(row=0, column=0, sticky="w", padx=20, pady=10)

        # Progress frame with modern styling
        progress_frame = ctk.CTkFrame(self.interview_frame, fg_color="transparent")
        progress_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=10)

        ctk.CTkLabel(
            progress_frame, text="Progress:", font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, sticky="w", padx=10, pady=5)

        self.progress_bar = ctk.CTkProgressBar(
            progress_frame, width=300, height=20, corner_radius=10
        )
        self.progress_bar.grid(row=0, column=1, sticky="ew", padx=10, pady=5)
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            progress_frame, text="0/20", font=ctk.CTkFont(size=14, weight="bold")
        )
        self.progress_label.grid(row=0, column=2, padx=10, pady=5)
        progress_frame.grid_columnconfigure(1, weight=1)

        # Analysis frame with modern styling
        analysis_frame = ctk.CTkFrame(
            self.interview_frame, fg_color="#2B2B2B", corner_radius=10
        )
        analysis_frame.grid(row=4, column=0, sticky="nsew", padx=20, pady=(10, 20))
        analysis_frame.grid_rowconfigure(1, weight=1)
        analysis_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            analysis_frame,
            text="Response Analysis:",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 10))

        self.analysis_text = ctk.CTkTextbox(
            analysis_frame,
            height=150,
            corner_radius=8,
            border_width=2,
            border_color="#1E90FF",
        )
        self.analysis_text.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.analysis_text.configure(state="disabled")

    def draw_avatar(self):
        """Draw AI avatar"""
        self.avatar_canvas.delete("all")
        # Draw AI face
        self.avatar_canvas.create_oval(20, 20, 80, 80, fill="#1E90FF", outline="")
        # Draw eyes
        self.avatar_canvas.create_oval(35, 40, 45, 50, fill="white", outline="")
        self.avatar_canvas.create_oval(55, 40, 65, 50, fill="white", outline="")
        # Draw pupils
        self.avatar_canvas.create_oval(38, 43, 42, 47, fill="black", outline="")
        self.avatar_canvas.create_oval(58, 43, 62, 47, fill="black", outline="")
        # Draw mouth
        self.avatar_canvas.create_arc(
            30,
            50,
            70,
            70,
            start=0,
            extent=180,
            fill="",
            outline="white",
            width=2,
            style="arc",
        )

    def draw_recording_indicator(self):
        """Draw recording indicator"""
        self.recording_canvas.delete("all")
        color = "#FF6347" if self.agent.is_recording else "#A9A9A9"
        self.recording_canvas.create_oval(10, 10, 30, 30, fill=color, outline="")

        if self.agent.is_recording:
            # Start pulse animation
            self.start_pulse_animation()
        else:
            # Stop pulse animation
            self.stop_pulse_animation()

    def draw_spinner(self):
        """Draw loading spinner"""
        self.spinner_canvas.delete("all")
        center_x, center_y = 50, 50
        radius = 30

        # Draw spinner arcs
        for i in range(8):
            start_angle = self.spinner_angle + i * 45
            extent = 30
            color_intensity = 255 - i * 30
            color = f"#{color_intensity:02x}{color_intensity:02x}{color_intensity:02x}"

            self.spinner_canvas.create_arc(
                center_x - radius,
                center_y - radius,
                center_x + radius,
                center_y + radius,
                start=start_angle,
                extent=extent,
                outline=color,
                width=5,
                style="arc",
            )

        # Update angle for next frame
        self.spinner_angle = (self.spinner_angle + 10) % 360

        # Schedule next animation frame
        self.spinner_animation = self.root.after(50, self.draw_spinner)

    def start_spinner(self):
        """Start spinner animation"""
        if self.spinner_animation is None:
            self.draw_spinner()

    def stop_spinner(self):
        """Stop spinner animation"""
        if self.spinner_animation is not None:
            self.root.after_cancel(self.spinner_animation)
            self.spinner_animation = None

    def start_pulse_animation(self):
        """Start pulse animation for recording indicator"""
        if self.pulse_animation is None:
            self.pulse_animation = self.root.after(100, self.pulse_recording_indicator)

    def stop_pulse_animation(self):
        """Stop pulse animation for recording indicator"""
        if self.pulse_animation is not None:
            self.root.after_cancel(self.pulse_animation)
            self.pulse_animation = None

    def pulse_recording_indicator(self):
        """Animate recording indicator with pulse effect"""
        if self.agent.is_recording:
            self.recording_canvas.delete("all")

            # Update pulse size
            if self.pulse_growing:
                self.pulse_size += 2
                if self.pulse_size >= 15:
                    self.pulse_growing = False
            else:
                self.pulse_size -= 2
                if self.pulse_size <= 5:
                    self.pulse_growing = True

            # Draw pulse circles
            center = 20
            self.recording_canvas.create_oval(
                center - self.pulse_size,
                center - self.pulse_size,
                center + self.pulse_size,
                center + self.pulse_size,
                outline="#FF6347",
                width=2,
            )

            # Draw center circle
            self.recording_canvas.create_oval(
                10, 10, 30, 30, fill="#FF6347", outline=""
            )

            # Schedule next animation frame
            self.pulse_animation = self.root.after(100, self.pulse_recording_indicator)

    def process_update_queue(self):
        """Process updates from background threads"""
        try:
            while not self.update_queue.empty():
                update = self.update_queue.get_nowait()
                if callable(update):
                    update()
        except queue.Empty:
            pass

        # Schedule next check
        self.root.after(100, self.process_update_queue)

    def start_interview(self):
        """Start the interview process"""
        job_title = self.job_title_var.get().strip()
        candidate_id = self.candidate_id_var.get().strip()
        job_description = self.job_description_text.get("1.0", "end").strip()

        if not job_title or not candidate_id or not job_description:
            messagebox.showerror("Error", "Please fill in all fields")
            return

        # Disable start button
        self.start_button.configure(state="disabled")

        # Show loading frame
        self.setup_frame.grid_remove()
        self.loading_frame.grid()
        self.start_spinner()

        # Create session in a separate thread to avoid blocking GUI
        def create_session():
            try:
                session_id = self.agent.create_interview_session(
                    job_title, job_description, candidate_id
                )

                # Update GUI in main thread
                self.update_queue.put(lambda: self.session_created(session_id))
            except Exception as e:
                logger.error(f"Error creating session: {e}")
                self.update_queue.put(lambda: self.session_creation_failed())

        thread = threading.Thread(target=create_session)
        thread.daemon = True
        thread.start()

    def session_created(self, session_id):
        """Handle session creation"""
        # Stop spinner
        self.stop_spinner()

        # Hide loading frame
        self.loading_frame.grid_remove()

        # Start interview
        if self.agent.start_interview(session_id):
            # Show interview frame
            self.interview_frame.grid()

            # Enable controls
            self.end_button.configure(state="normal")

            # Get first question
            self.next_question()

            self.status_var.set(
                "Interview started. AI will ask questions automatically."
            )
        else:
            messagebox.showerror("Error", "Failed to start interview")
            # Return to setup page
            self.interview_frame.grid_remove()
            self.setup_frame.grid()
            self.start_button.configure(state="normal")

    def session_creation_failed(self):
        """Handle session creation failure"""
        # Stop spinner
        self.stop_spinner()

        # Hide loading frame
        self.loading_frame.grid_remove()

        # Show setup frame
        self.setup_frame.grid()
        self.start_button.configure(state="normal")

        messagebox.showerror("Error", "Failed to create interview session")

    def next_question(self):
        """Get the next question"""
        # Disable next button until analysis is complete
        self.next_button.configure(state="disabled")

        # Update status
        self.status_var.set("Generating next question...")

        # Get next question in a separate thread to avoid blocking GUI
        def get_question():
            try:
                question = self.agent.get_next_question()

                # Update GUI in main thread
                self.update_queue.put(lambda: self.question_received(question))
            except Exception as e:
                logger.error(f"Error getting question: {e}")
                self.update_queue.put(
                    lambda: self.status_var.set("Error getting question")
                )

        thread = threading.Thread(target=get_question)
        thread.daemon = True
        thread.start()

    def question_received(self, question):
        """Handle received question"""
        if question:
            self.current_question_var.set(question.text)
            self.question_label.configure(text=question.text)

            # Define callback to start recording after TTS finishes
            def start_recording_callback():
                # This will be called after TTS finishes
                self.update_queue.put(self._auto_start_recording)

            # Convert question to speech with callback
            self.agent.text_to_speech(question.text, callback=start_recording_callback)

            # Update progress
            progress = self.agent.get_session_progress()
            self.progress_bar.set(progress["questions_asked"] / 20)
            self.progress_label.configure(text=f"{progress['questions_asked']}/20")

            # Clear analysis
            self.analysis_text.configure(state="normal")
            self.analysis_text.delete("1.0", "end")
            self.analysis_text.configure(state="disabled")

            self.status_var.set(
                "AI is asking the question. Recording will start automatically."
            )
        else:
            self.status_var.set("No more questions available.")

    def _auto_start_recording(self):
        """Automatically start recording after question is read"""
        if self.agent.start_recording():
            self.agent.is_recording = True
            self.recording_label.configure(text="Recording", text_color="#FF6347")
            self.stop_button.configure(state="normal")  # Enable stop button
            self.recording_start_time = time.time()
            self.update_recording_time()
            self.draw_recording_indicator()  # Update recording indicator
            self.status_var.set("Recording started automatically. Speak your answer.")

            # Start silence detection
            self.agent.check_silence_and_stop()

    def stop_recording(self):
        """Manually stop recording"""
        if self.agent.is_recording:
            self.status_var.set("Stopping recording...")
            self.stop_button.configure(state="disabled")
            self.recording_label.configure(text="Processing", text_color="#1E90FF")
            self.draw_recording_indicator()  # Update recording indicator

            # Call agent's stop_recording_and_analyze with callback
            self.agent.stop_recording_and_analyze(callback=self.process_analysis_result)

    def update_recording_time(self):
        """Update recording time display"""
        if self.agent.is_recording and hasattr(self, "recording_start_time"):
            elapsed = int(time.time() - self.recording_start_time)
            minutes = elapsed // 60
            seconds = elapsed % 60
            self.recording_time_var.set(f"{minutes:02d}:{seconds:02d}")

            # Schedule next update
            self.root.after(1000, self.update_recording_time)

    def process_analysis_result(self, result):
        """Process the analysis result and update GUI"""
        if result:
            # Update analysis display
            self.analysis_text.configure(state="normal")
            self.analysis_text.delete("1.0", "end")

            analysis_text = f"""Transcribed Text:
{result['transcribed_text']}
Scores:
- Technical: {result['scores']['technical']:.2f}
- Communication: {result['scores']['communication']:.2f}
- Confidence: {result['scores']['confidence']:.2f}
- Sentiment: {result['scores']['sentiment']:.2f}
"""

            self.analysis_text.insert("1.0", analysis_text)
            self.analysis_text.configure(state="disabled")

            # Reset recording indicator
            self.recording_label.configure(text="Not Recording", text_color="#A9A9A9")
            self.draw_recording_indicator()  # Update recording indicator
            self.stop_button.configure(state="disabled")

            # Check if interview should end
            if self.agent.should_end_interview():
                self.status_var.set(
                    "Interview complete. Click 'End Interview' to generate report."
                )
                self.next_button.configure(state="disabled")
            else:
                self.status_var.set(
                    "Response analyzed. Next question will begin shortly."
                )
                # Automatically move to next question after a short delay
                self.root.after(2000, self.next_question)
        else:
            self.status_var.set("Error analyzing response. Please try again.")
            self.recording_label.configure(text="Not Recording", text_color="#A9A9A9")
            self.draw_recording_indicator()  # Update recording indicator
            self.stop_button.configure(state="disabled")
            self.next_button.configure(
                state="normal"
            )  # Enable next button to allow retry

    def end_interview(self):
        """End the interview"""
        result = messagebox.askyesno(
            "End Interview", "Are you sure you want to end the interview?"
        )

        if result:
            self.status_var.set("Ending interview and generating report...")

            # End interview in separate thread
            def end_interview_thread():
                success = self.agent.end_interview()

                # Update GUI in main thread
                self.update_queue.put(lambda: self.interview_ended(success))

            thread = threading.Thread(target=end_interview_thread)
            thread.daemon = True
            thread.start()

    def interview_ended(self, success):
        """Handle interview completion"""
        if success:
            self.status_var.set("Interview completed successfully!")
            messagebox.showinfo("Success", "Interview completed and report generated!")

            # Reset GUI
            self.reset_gui()
        else:
            self.status_var.set("Error ending interview.")
            messagebox.showerror("Error", "Failed to end interview")

    def show_report_generated(self, report_path):
        """Show report generated notification"""
        messagebox.showinfo(
            "Report Generated",
            f"Interview report has been generated and saved to:\n{report_path}",
        )

    def reset_gui(self):
        """Reset GUI to initial state"""
        # Hide interview frame
        self.interview_frame.grid_remove()

        # Show setup frame
        self.setup_frame.grid()
        self.start_button.configure(state="normal")

        # Clear input fields
        self.job_title_var.set("")
        self.candidate_id_var.set("")
        self.job_description_text.delete("1.0", "end")

        # Reset variables
        self.current_question_var.set("")
        self.recording_time_var.set("00:00")
        self.status_var.set("Ready to start")

        # Reset progress
        self.progress_bar.set(0)
        self.progress_label.configure(text="0/20")

        # Clear analysis
        self.analysis_text.configure(state="normal")
        self.analysis_text.delete("1.0", "end")
        self.analysis_text.configure(state="disabled")

        # Reset recording indicator
        self.recording_label.configure(text="Not Recording", text_color="#A9A9A9")
        self.draw_recording_indicator()  # Update recording indicator
        self.stop_button.configure(state="disabled")
        self.next_button.configure(state="disabled")

    def run(self):
        """Run the GUI application"""
        # Handle window resize
        self.root.bind("<Configure>", self.on_window_resize)

        # Start the GUI
        self.root.mainloop()

    def on_window_resize(self, event):
        """Handle window resize events"""
        # Update wraplength for question label based on window width
        if event.widget == self.root:
            new_width = max(400, event.width - 200)  # Minimum width of 400
            self.question_label.configure(wraplength=new_width)
