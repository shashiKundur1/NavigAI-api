"""
Main application entry point for the NavigAI Mock Interview System
This file provides a complete GUI application for conducting AI-powered mock interviews
"""

import sys
import os
import logging
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("mock_interview.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

try:
    import customtkinter as ctk
    from tkinter import messagebox, filedialog
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    # Import our modules
    from agents.mock_interview_agent import MockInterviewAgent, MockInterviewGUI
    from services.mock_interview_service import MockInterviewService
    import db.firebase as firebase_db
    from models.mock_interview import InterviewSession

except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    print("Please install all required dependencies:")
    print("pip install -r requirements.txt")
    sys.exit(1)


class EnhancedMockInterviewGUI(MockInterviewGUI):
    """Enhanced GUI with additional features and better user experience"""

    def __init__(self):
        super().__init__()

        # Additional features
        self.settings_window = None
        self.help_window = None
        self.history_window = None

        # Create menu bar
        self.create_menu_bar()

        # Create status bar
        self.create_status_bar()

        # Load settings
        self.load_settings()

        # Set up window
        self.setup_window()

    def create_menu_bar(self):
        """Create menu bar for the application"""
        menubar = ctk.CTkFrame(self.root, height=30)
        menubar.pack(fill="x", side="top")

        # File menu
        file_menu = ctk.CTkButton(menubar, text="File", command=self.show_file_menu)
        file_menu.pack(side="left", padx=5)

        # View menu
        view_menu = ctk.CTkButton(menubar, text="View", command=self.show_view_menu)
        view_menu.pack(side="left", padx=5)

        # Help menu
        help_menu = ctk.CTkButton(menubar, text="Help", command=self.show_help_menu)
        help_menu.pack(side="left", padx=5)

    def create_status_bar(self):
        """Create status bar"""
        status_frame = ctk.CTkFrame(self.root, height=25)
        status_frame.pack(fill="x", side="bottom")

        self.status_bar_label = ctk.CTkLabel(
            status_frame, text="Ready", font=ctk.CTkFont(size=10)
        )
        self.status_bar_label.pack(side="left", padx=10)

        # Connection status
        self.connection_status = ctk.CTkLabel(
            status_frame,
            text="● Connected",
            text_color="green",
            font=ctk.CTkFont(size=10),
        )
        self.connection_status.pack(side="right", padx=10)

    def setup_window(self):
        """Set up the main window"""
        self.root.title("NavigAI - AI Mock Interview System")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)

        # Center window
        self.center_window()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def center_window(self):
        """Center the window on the screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def create_widgets(self):
        """Create enhanced widgets"""
        # Create main container with tabs
        self.tab_view = ctk.CTkTabview(self.root)
        self.tab_view.pack(fill="both", expand=True, padx=20, pady=20)

        # Create tabs
        self.interview_tab = self.tab_view.add("Interview")
        self.history_tab = self.tab_view.add("History")
        self.analytics_tab = self.tab_view.add("Analytics")
        self.settings_tab = self.tab_view.add("Settings")

        # Setup each tab
        self.setup_interview_tab()
        self.setup_history_tab()
        self.setup_analytics_tab()
        self.setup_settings_tab()

    def setup_interview_tab(self):
        """Setup the interview tab"""
        # Main container for interview
        interview_frame = ctk.CTkFrame(self.interview_tab)
        interview_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Create two columns
        left_column = ctk.CTkFrame(interview_frame)
        left_column.pack(side="left", fill="both", expand=True, padx=(0, 10))

        right_column = ctk.CTkFrame(interview_frame)
        right_column.pack(side="right", fill="both", expand=True, padx=(10, 0))

        # Setup left column (input and controls)
        self.setup_input_section(left_column)
        self.setup_controls_section(left_column)

        # Setup right column (question and analysis)
        self.setup_question_section(right_column)
        self.setup_analysis_section(right_column)

    def setup_input_section(self, parent):
        """Setup input section"""
        input_frame = ctk.CTkFrame(parent)
        input_frame.pack(fill="x", padx=10, pady=10)

        # Title
        title_label = ctk.CTkLabel(
            input_frame,
            text="Interview Setup",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title_label.pack(pady=(10, 20))

        # Job title
        job_frame = ctk.CTkFrame(input_frame)
        job_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(job_frame, text="Job Title:").pack(anchor="w", padx=5)
        self.job_title_entry = ctk.CTkEntry(job_frame, width=300)
        self.job_title_entry.pack(fill="x", padx=5, pady=5)

        # Candidate ID
        candidate_frame = ctk.CTkFrame(input_frame)
        candidate_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(candidate_frame, text="Candidate ID:").pack(anchor="w", padx=5)
        self.candidate_id_entry = ctk.CTkEntry(candidate_frame, width=300)
        self.candidate_id_entry.pack(fill="x", padx=5, pady=5)

        # Job description
        desc_frame = ctk.CTkFrame(input_frame)
        desc_frame.pack(fill="both", expand=True, padx=10, pady=5)

        ctk.CTkLabel(desc_frame, text="Job Description:").pack(anchor="w", padx=5)
        self.job_description_text = ctk.CTkTextbox(desc_frame, height=150)
        self.job_description_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Start button
        self.start_button = ctk.CTkButton(
            input_frame,
            text="Start Interview",
            command=self.start_interview,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.start_button.pack(pady=20)

    def setup_controls_section(self, parent):
        """Setup controls section"""
        controls_frame = ctk.CTkFrame(parent)
        controls_frame.pack(fill="x", padx=10, pady=10)

        # Title
        title_label = ctk.CTkLabel(
            controls_frame,
            text="Interview Controls",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title_label.pack(pady=(10, 20))

        # Recording controls
        recording_frame = ctk.CTkFrame(controls_frame)
        recording_frame.pack(fill="x", padx=10, pady=10)

        self.record_button = ctk.CTkButton(
            recording_frame,
            text="Start Recording",
            command=self.toggle_recording,
            height=50,
            width=200,
            state="disabled",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.record_button.pack(pady=10)

        # Recording time
        self.recording_time_label = ctk.CTkLabel(
            recording_frame, text="00:00", font=ctk.CTkFont(size=24, weight="bold")
        )
        self.recording_time_label.pack(pady=5)

        # Navigation buttons
        nav_frame = ctk.CTkFrame(controls_frame)
        nav_frame.pack(fill="x", padx=10, pady=10)

        self.next_button = ctk.CTkButton(
            nav_frame,
            text="Next Question",
            command=self.next_question,
            height=40,
            width=150,
            state="disabled",
        )
        self.next_button.pack(side="left", padx=5, pady=5)

        self.end_button = ctk.CTkButton(
            nav_frame,
            text="End Interview",
            command=self.end_interview,
            height=40,
            width=150,
            state="disabled",
            fg_color="red",
            hover_color="darkred",
        )
        self.end_button.pack(side="left", padx=5, pady=5)

        # Progress
        progress_frame = ctk.CTkFrame(controls_frame)
        progress_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(progress_frame, text="Progress:").pack(anchor="w", padx=5)

        progress_container = ctk.CTkFrame(progress_frame)
        progress_container.pack(fill="x", padx=5, pady=5)

        self.progress_bar = ctk.CTkProgressBar(progress_container, width=300)
        self.progress_bar.pack(side="left", padx=5)
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(progress_container, text="0/10")
        self.progress_label.pack(side="left", padx=5)

    def setup_question_section(self, parent):
        """Setup question display section"""
        question_frame = ctk.CTkFrame(parent)
        question_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Title
        title_label = ctk.CTkLabel(
            question_frame,
            text="Current Question",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title_label.pack(pady=(10, 20))

        # Question display
        question_container = ctk.CTkFrame(question_frame)
        question_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.question_label = ctk.CTkLabel(
            question_container,
            text="Click 'Start Interview' to begin",
            font=ctk.CTkFont(size=14),
            wraplength=400,
            justify="left",
        )
        self.question_label.pack(padx=20, pady=20, anchor="w")

        # Question info
        info_frame = ctk.CTkFrame(question_frame)
        info_frame.pack(fill="x", padx=10, pady=10)

        self.question_info_label = ctk.CTkLabel(
            info_frame, text="", font=ctk.CTkFont(size=12)
        )
        self.question_info_label.pack(padx=10, pady=5)

    def setup_analysis_section(self, parent):
        """Setup analysis section"""
        analysis_frame = ctk.CTkFrame(parent)
        analysis_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Title
        title_label = ctk.CTkLabel(
            analysis_frame,
            text="Response Analysis",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title_label.pack(pady=(10, 20))

        # Analysis display
        self.analysis_text = ctk.CTkTextbox(
            analysis_frame, height=200, state="disabled"
        )
        self.analysis_text.pack(fill="both", expand=True, padx=10, pady=10)

        # Scores display
        scores_frame = ctk.CTkFrame(analysis_frame)
        scores_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            scores_frame, text="Scores:", font=ctk.CTkFont(size=14, weight="bold")
        ).pack(anchor="w", padx=10, pady=5)

        self.scores_frame = ctk.CTkFrame(scores_frame)
        self.scores_frame.pack(fill="x", padx=10, pady=5)

    def setup_history_tab(self):
        """Setup history tab"""
        history_frame = ctk.CTkFrame(self.history_tab)
        history_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Title
        title_label = ctk.CTkLabel(
            history_frame,
            text="Interview History",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title_label.pack(pady=(10, 20))

        # History list
        self.history_listbox = ctk.CTkTextbox(history_frame, state="disabled")
        self.history_listbox.pack(fill="both", expand=True, padx=10, pady=10)

        # Buttons
        button_frame = ctk.CTkFrame(history_frame)
        button_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(button_frame, text="Refresh", command=self.refresh_history).pack(
            side="left", padx=5
        )

        ctk.CTkButton(
            button_frame, text="View Details", command=self.view_session_details
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            button_frame, text="Download Report", command=self.download_report
        ).pack(side="left", padx=5)

    def setup_analytics_tab(self):
        """Setup analytics tab"""
        analytics_frame = ctk.CTkFrame(self.analytics_tab)
        analytics_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Title
        title_label = ctk.CTkLabel(
            analytics_frame,
            text="Performance Analytics",
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title_label.pack(pady=(10, 20))

        # Analytics display
        self.analytics_frame = ctk.CTkFrame(analytics_frame)
        self.analytics_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Refresh button
        ctk.CTkButton(
            analytics_frame, text="Refresh Analytics", command=self.refresh_analytics
        ).pack(pady=10)

    def setup_settings_tab(self):
        """Setup settings tab"""
        settings_frame = ctk.CTkFrame(self.settings_tab)
        settings_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Title
        title_label = ctk.CTkLabel(
            settings_frame, text="Settings", font=ctk.CTkFont(size=18, weight="bold")
        )
        title_label.pack(pady=(10, 20))

        # Audio settings
        audio_frame = ctk.CTkFrame(settings_frame)
        audio_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            audio_frame, text="Audio Settings", font=ctk.CTkFont(size=16, weight="bold")
        ).pack(anchor="w", padx=10, pady=5)

        # Sample rate
        sample_rate_frame = ctk.CTkFrame(audio_frame)
        sample_rate_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(sample_rate_frame, text="Sample Rate:").pack(side="left", padx=5)
        self.sample_rate_var = ctk.StringVar(value="16000")
        sample_rate_combo = ctk.CTkComboBox(
            sample_rate_frame,
            variable=self.sample_rate_var,
            values=["8000", "16000", "22050", "44100"],
            width=150,
        )
        sample_rate_combo.pack(side="left", padx=5)

        # AI Model settings
        model_frame = ctk.CTkFrame(settings_frame)
        model_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            model_frame,
            text="AI Model Settings",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=10, pady=5)

        # Whisper model
        whisper_frame = ctk.CTkFrame(model_frame)
        whisper_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(whisper_frame, text="Whisper Model:").pack(side="left", padx=5)
        self.whisper_model_var = ctk.StringVar(value="turbo")
        whisper_combo = ctk.CTkComboBox(
            whisper_frame,
            variable=self.whisper_model_var,
            values=["tiny", "base", "small", "medium", "large", "turbo"],
            width=150,
        )
        whisper_combo.pack(side="left", padx=5)

        # Save button
        ctk.CTkButton(
            settings_frame,
            text="Save Settings",
            command=self.save_settings,
            height=40,
            width=150,
        ).pack(pady=20)

    def show_file_menu(self):
        """Show file menu options"""
        menu = ctk.CTkToplevel(self.root)
        menu.title("File Menu")
        menu.geometry("200x150")

        ctk.CTkButton(
            menu,
            text="New Interview",
            command=lambda: [menu.destroy(), self.reset_gui()],
        ).pack(pady=5)
        ctk.CTkButton(
            menu,
            text="Open Report",
            command=lambda: [menu.destroy(), self.open_report()],
        ).pack(pady=5)
        ctk.CTkButton(
            menu, text="Exit", command=lambda: [menu.destroy(), self.on_closing()]
        ).pack(pady=5)

    def show_view_menu(self):
        """Show view menu options"""
        menu = ctk.CTkToplevel(self.root)
        menu.title("View Menu")
        menu.geometry("200x150")

        ctk.CTkButton(
            menu,
            text="Interview",
            command=lambda: [menu.destroy(), self.tab_view.set("Interview")],
        ).pack(pady=5)
        ctk.CTkButton(
            menu,
            text="History",
            command=lambda: [menu.destroy(), self.tab_view.set("History")],
        ).pack(pady=5)
        ctk.CTkButton(
            menu,
            text="Analytics",
            command=lambda: [menu.destroy(), self.tab_view.set("Analytics")],
        ).pack(pady=5)
        ctk.CTkButton(
            menu,
            text="Settings",
            command=lambda: [menu.destroy(), self.tab_view.set("Settings")],
        ).pack(pady=5)

    def show_help_menu(self):
        """Show help menu options"""
        menu = ctk.CTkToplevel(self.root)
        menu.title("Help Menu")
        menu.geometry("200x150")

        ctk.CTkButton(
            menu,
            text="User Guide",
            command=lambda: [menu.destroy(), self.show_user_guide()],
        ).pack(pady=5)
        ctk.CTkButton(
            menu, text="About", command=lambda: [menu.destroy(), self.show_about()]
        ).pack(pady=5)
        ctk.CTkButton(
            menu,
            text="Check Updates",
            command=lambda: [menu.destroy(), self.check_updates()],
        ).pack(pady=5)

    def show_user_guide(self):
        """Show user guide"""
        guide_window = ctk.CTkToplevel(self.root)
        guide_window.title("User Guide")
        guide_window.geometry("600x500")

        guide_text = ctk.CTkTextbox(guide_window, wrap="word")
        guide_text.pack(fill="both", expand=True, padx=10, pady=10)

        guide_content = """
NavigAI Mock Interview System - User Guide
Getting Started:
1. Fill in the Job Title, Candidate ID, and Job Description
2. Click 'Start Interview' to begin
3. Read the question and click 'Start Recording' to answer
4. Click 'Stop Recording' when finished
5. Review the analysis and click 'Next Question' to continue
6. Click 'End Interview' when finished to generate a report
Tips:
- Speak clearly and at a moderate pace
- Answer questions thoroughly but concisely
- Use the expected keywords when possible
- Stay calm and confident
Features:
- AI-powered question selection using Thompson Sampling
- Real-time speech-to-text transcription
- Multi-modal response analysis
- Comprehensive performance reports
- Interview history and analytics
"""

        guide_text.insert("1.0", guide_content)
        guide_text.configure(state="disabled")

    def show_about(self):
        """Show about dialog"""
        about_window = ctk.CTkToplevel(self.root)
        about_window.title("About NavigAI")
        about_window.geometry("400x300")

        about_text = """
NavigAI Mock Interview System
Version 1.0.0
An AI-powered platform for conducting realistic mock interviews and providing comprehensive feedback to help candidates improve their interview skills.
Features:
• Adaptive Question Selection
• Real-time Analysis
• Performance Tracking
• Detailed Reports
© 2024 NavigAI Team
"""

        label = ctk.CTkLabel(about_window, text=about_text, justify="left")
        label.pack(padx=20, pady=20)

    def check_updates(self):
        """Check for updates"""
        messagebox.showinfo(
            "Check Updates", "You are using the latest version of NavigAI."
        )

    def refresh_history(self):
        """Refresh interview history"""
        try:
            # Get all sessions from Firebase
            all_sessions = firebase_db.get_all_interview_sessions()

            # Update history display
            self.history_listbox.configure(state="normal")
            self.history_listbox.delete("1.0", "end")

            for session_data in all_sessions:
                session = InterviewSession(**session_data)

                history_entry = f"""
Session ID: {session.id}
Job Title: {session.job_title}
Candidate ID: {session.candidate_id}
Status: {session.status.value}
Created: {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}
Questions: {len(session.questions_asked)}
Answers: {len(session.answers)}
{'-' * 50}
"""

                self.history_listbox.insert("end", history_entry)

            self.history_listbox.configure(state="disabled")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh history: {str(e)}")

    def view_session_details(self):
        """View session details"""
        messagebox.showinfo("Session Details", "Session details feature coming soon!")

    def download_report(self):
        """Download report"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )

        if file_path:
            messagebox.showinfo(
                "Download Report", f"Report will be saved to: {file_path}"
            )

    def refresh_analytics(self):
        """Refresh analytics"""
        try:
            # Clear existing analytics
            for widget in self.analytics_frame.winfo_children():
                widget.destroy()

            # Create analytics display
            analytics_label = ctk.CTkLabel(
                self.analytics_frame,
                text="Performance Analytics",
                font=ctk.CTkFont(size=16, weight="bold"),
            )
            analytics_label.pack(pady=10)

            # Create a simple chart
            self.create_analytics_chart()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh analytics: {str(e)}")

    def create_analytics_chart(self):
        """Create analytics chart"""
        try:
            # Sample data
            categories = ["Technical", "Communication", "Confidence", "Sentiment"]
            scores = [0.75, 0.82, 0.68, 0.79]

            # Create matplotlib figure
            fig, ax = plt.subplots(figsize=(8, 6))
            bars = ax.bar(
                categories, scores, color=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
            )

            ax.set_ylim(0, 1)
            ax.set_ylabel("Score")
            ax.set_title("Average Performance Metrics")

            # Add value labels on bars
            for bar, score in zip(bars, scores):
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height + 0.01,
                    f"{score:.2f}",
                    ha="center",
                    va="bottom",
                )

            # Embed in tkinter
            canvas = FigureCanvasTkAgg(fig, master=self.analytics_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        except Exception as e:
            error_label = ctk.CTkLabel(
                self.analytics_frame,
                text=f"Failed to create chart: {str(e)}",
                text_color="red",
            )
            error_label.pack(pady=20)

    def load_settings(self):
        """Load settings from file"""
        try:
            if os.path.exists("settings.json"):
                import json

                with open("settings.json", "r") as f:
                    settings = json.load(f)

                self.sample_rate_var.set(settings.get("sample_rate", "16000"))
                self.whisper_model_var.set(settings.get("whisper_model", "turbo"))

        except Exception as e:
            logger.error(f"Failed to load settings: {e}")

    def save_settings(self):
        """Save settings to file"""
        try:
            settings = {
                "sample_rate": self.sample_rate_var.get(),
                "whisper_model": self.whisper_model_var.get(),
            }

            import json

            with open("settings.json", "w") as f:
                json.dump(settings, f, indent=2)

            messagebox.showinfo("Settings", "Settings saved successfully!")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")

    def update_status_bar(self, message):
        """Update status bar message"""
        self.status_bar_label.configure(text=message)
        self.root.update_idletasks()

    def update_connection_status(self, connected):
        """Update connection status"""
        if connected:
            self.connection_status.configure(text="● Connected", text_color="green")
        else:
            self.connection_status.configure(text="● Disconnected", text_color="red")

    def on_closing(self):
        """Handle window closing"""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            # Stop any recording
            if self.agent.is_recording:
                self.agent.stop_recording()

            # Save settings
            self.save_settings()

            # Close application
            self.root.destroy()
            sys.exit(0)

    def reset_gui(self):
        """Reset GUI to initial state"""
        # Clear input fields
        self.job_title_entry.delete(0, "end")
        self.candidate_id_entry.delete(0, "end")
        self.job_description_text.delete("1.0", "end")

        # Reset interview state
        self.agent.current_session = None
        self.agent.current_question = None

        # Reset GUI elements
        self.record_button.configure(text="Start Recording", state="disabled")
        self.next_button.configure(state="disabled")
        self.end_button.configure(state="disabled")
        self.start_button.configure(state="normal")

        # Reset progress
        self.progress_bar.set(0)
        self.progress_label.configure(text="0/10")
        self.recording_time_label.configure(text="00:00")

        # Clear displays
        self.question_label.configure(text="Click 'Start Interview' to begin")
        self.question_info_label.configure(text="")

        self.analysis_text.configure(state="normal")
        self.analysis_text.delete("1.0", "end")
        self.analysis_text.configure(state="disabled")

        # Clear scores
        for widget in self.scores_frame.winfo_children():
            widget.destroy()

    def process_analysis_result(self, result):
        """Process analysis result and update GUI"""
        super().process_analysis_result(result)

        if result:
            # Update scores display
            self.update_scores_display(result["scores"])

    def update_scores_display(self, scores):
        """Update scores display"""
        # Clear existing scores
        for widget in self.scores_frame.winfo_children():
            widget.destroy()

        # Create score displays
        score_items = [
            ("Technical", scores["technical"], "#1f77b4"),
            ("Communication", scores["communication"], "#ff7f0e"),
            ("Confidence", scores["confidence"], "#2ca02c"),
            ("Sentiment", scores["sentiment"], "#d62728"),
        ]

        for label, score, color in score_items:
            score_frame = ctk.CTkFrame(self.scores_frame)
            score_frame.pack(fill="x", padx=5, pady=2)

            ctk.CTkLabel(score_frame, text=f"{label}:", width=100).pack(
                side="left", padx=5
            )

            # Progress bar for score
            progress_bar = ctk.CTkProgressBar(score_frame, width=200)
            progress_bar.pack(side="left", padx=5)
            progress_bar.set(score)

            # Score value
            ctk.CTkLabel(score_frame, text=f"{score:.2f}", width=50).pack(
                side="left", padx=5
            )

    def start_interview(self):
        """Start interview with enhanced error handling"""
        try:
            job_title = self.job_title_entry.get().strip()
            candidate_id = self.candidate_id_entry.get().strip()
            job_description = self.job_description_text.get("1.0", "end").strip()

            if not job_title or not candidate_id or not job_description:
                messagebox.showerror("Error", "Please fill in all fields")
                return

            self.update_status_bar("Starting interview...")

            # Create session
            session_id = self.agent.create_interview_session(
                job_title, job_description, candidate_id
            )

            # Start interview
            if self.agent.start_interview(session_id):
                # Update GUI
                self.record_button.configure(state="normal")
                self.end_button.configure(state="normal")
                self.start_button.configure(state="disabled")

                # Get first question
                self.next_question()

                self.update_status_bar("Interview started. Ready for first question.")
                self.update_connection_status(True)
            else:
                messagebox.showerror("Error", "Failed to start interview")
                self.update_status_bar("Failed to start interview")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to start interview: {str(e)}")
            self.update_status_bar(f"Error: {str(e)}")


def main():
    """Main function to run the application"""
    try:
        # Set up CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Create and run application
        app = EnhancedMockInterviewGUI()
        app.run()

    except Exception as e:
        logger.error(f"Application error: {e}")
        messagebox.showerror(
            "Application Error", f"Failed to start application: {str(e)}"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
