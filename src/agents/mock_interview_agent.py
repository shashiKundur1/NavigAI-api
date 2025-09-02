import threading
import time
from typing import Optional, Dict, Any
import customtkinter as ctk
from tkinter import messagebox, filedialog

from models.mock_interview import InterviewSession, Question, Answer, InterviewStatus
from services.mock_interview_service import MockInterviewService
import db.firebase as firebase_db


class MockInterviewAgent:
    """Main agent for coordinating the AI mock interview process"""

    def __init__(self):
        self.service = MockInterviewService()
        self.current_session: Optional[InterviewSession] = None
        self.current_question: Optional[Question] = None
        self.is_recording = False
        self.recording_thread = None
        self.gui = None

    def create_interview_session(
        self, job_title: str, job_description: str, candidate_id: str
    ) -> str:
        """Create a new interview session"""
        session = self.service.create_interview_session(
            job_title, job_description, candidate_id
        )
        self.current_session = session
        return session.id

    def start_interview(self, session_id: str) -> bool:
        """Start the interview session"""
        success = self.service.start_interview(session_id)
        if success:
            session_data = firebase_db.get_interview_session(session_id)
            if session_data:
                self.current_session = InterviewSession(**session_data)
        return success

    def get_next_question(self) -> Optional[Question]:
        """Get the next question for the interview"""
        if not self.current_session:
            return None

        question = self.service.get_next_question(self.current_session.id)
        self.current_question = question
        return question

    def start_recording(self):
        """Start recording audio"""
        if not self.current_session:
            return False

        self.is_recording = True
        self.service.start_audio_recording(self.current_session.id)
        return True

    def stop_recording_and_analyze(self) -> Optional[Dict[str, Any]]:
        """Stop recording and analyze the response"""
        if not self.current_session or not self.current_question:
            return None

        # Stop recording
        self.is_recording = False
        audio_file = self.service.stop_audio_recording()

        if not audio_file:
            return None

        # Transcribe audio
        transcribed_text = self.service.transcribe_audio(audio_file)

        # Analyze response
        answer = self.service.analyze_response(
            audio_file, transcribed_text, self.current_question, self.current_session
        )

        # Submit answer
        self.service.submit_answer(self.current_session.id, answer)

        # Clean up audio file
        import os

        if os.path.exists(audio_file):
            os.remove(audio_file)

        return {
            "transcribed_text": transcribed_text,
            "answer": answer,
            "scores": {
                "technical": answer.technical_score,
                "communication": (answer.fluency_score + answer.confidence_score) / 2,
                "confidence": answer.confidence_score,
                "sentiment": answer.sentiment_score,
            },
        }

    def should_end_interview(self) -> bool:
        """Check if interview should be ended"""
        if not self.current_session:
            return True

        return self.service.should_end_interview(self.current_session.id)

    def end_interview(self) -> bool:
        """End the interview and generate report"""
        if not self.current_session:
            return False

        # End interview session
        success = self.service.end_interview(self.current_session.id)

        if success:
            # Generate report
            report_path = self.service.generate_interview_report(
                self.current_session.id
            )

            if report_path:
                # Show success message
                if self.gui:
                    self.gui.show_report_generated(report_path)

        return success

    def text_to_speech(self, text: str):
        """Convert text to speech"""

        def speak():
            self.service.text_to_speech(text)

        # Run in separate thread to avoid blocking GUI
        thread = threading.Thread(target=speak)
        thread.daemon = True
        thread.start()

    def get_session_progress(self) -> Dict[str, Any]:
        """Get current session progress"""
        if not self.current_session:
            return {}

        return {
            "questions_asked": len(self.current_session.questions_asked),
            "current_question": (
                self.current_question.text if self.current_question else None
            ),
            "status": self.current_session.status.value,
            "answers_count": len(self.current_session.answers),
        }

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for current session"""
        if not self.current_session or not self.current_session.answers:
            return {}

        latest_answer = self.current_session.answers[-1]
        return {
            "latest_technical_score": latest_answer.technical_score,
            "latest_communication_score": (
                latest_answer.fluency_score + latest_answer.confidence_score
            )
            / 2,
            "latest_confidence_score": latest_answer.confidence_score,
            "average_technical_score": sum(
                a.technical_score for a in self.current_session.answers
            )
            / len(self.current_session.answers),
        }


class MockInterviewGUI:
    """GUI for the AI Mock Interview System"""

    def __init__(self):
        self.agent = MockInterviewAgent()
        self.agent.gui = self

        # Initialize CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Create main window
        self.root = ctk.CTk()
        self.root.title("NavigAI - Mock Interview System")
        self.root.geometry("1000x700")

        # Variables
        self.job_title_var = ctk.StringVar()
        self.job_description_var = ctk.StringVar()
        self.candidate_id_var = ctk.StringVar()
        self.current_question_var = ctk.StringVar()
        self.recording_time_var = ctk.StringVar(value="00:00")
        self.status_var = ctk.StringVar(value="Ready to start")

        # Recording state
        self.recording_start_time = None
        self.recording_timer = None

        # Create GUI elements
        self.create_widgets()

    def create_widgets(self):
        """Create all GUI widgets"""
        # Main container
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="AI Mock Interview System",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title_label.pack(pady=(0, 20))

        # Setup frame
        setup_frame = ctk.CTkFrame(main_frame)
        setup_frame.pack(fill="x", pady=(0, 20))

        # Job title
        ctk.CTkLabel(setup_frame, text="Job Title:").grid(
            row=0, column=0, sticky="w", padx=10, pady=5
        )
        job_title_entry = ctk.CTkEntry(
            setup_frame, textvariable=self.job_title_var, width=300
        )
        job_title_entry.grid(row=0, column=1, padx=10, pady=5)

        # Candidate ID
        ctk.CTkLabel(setup_frame, text="Candidate ID:").grid(
            row=0, column=2, sticky="w", padx=10, pady=5
        )
        candidate_id_entry = ctk.CTkEntry(
            setup_frame, textvariable=self.candidate_id_var, width=200
        )
        candidate_id_entry.grid(row=0, column=3, padx=10, pady=5)

        # Job description
        ctk.CTkLabel(setup_frame, text="Job Description:").grid(
            row=1, column=0, sticky="nw", padx=10, pady=5
        )
        job_description_text = ctk.CTkTextbox(setup_frame, width=600, height=100)
        job_description_text.grid(row=2, column=0, columnspan=4, padx=10, pady=5)

        # Store reference to job description text widget
        self.job_description_text = job_description_text

        # Start button
        start_button = ctk.CTkButton(
            setup_frame, text="Start Interview", command=self.start_interview, width=150
        )
        start_button.grid(row=3, column=1, columnspan=2, pady=10)

        # Interview frame
        self.interview_frame = ctk.CTkFrame(main_frame)
        self.interview_frame.pack(fill="both", expand=True, pady=(0, 20))

        # Question display
        question_frame = ctk.CTkFrame(self.interview_frame)
        question_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            question_frame,
            text="Current Question:",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=10, pady=5)

        self.question_label = ctk.CTkLabel(
            question_frame,
            text="Click 'Start Interview' to begin",
            font=ctk.CTkFont(size=14),
            wraplength=800,
        )
        self.question_label.pack(padx=10, pady=5)

        # Controls frame
        controls_frame = ctk.CTkFrame(self.interview_frame)
        controls_frame.pack(fill="x", padx=10, pady=10)

        # Recording controls
        self.record_button = ctk.CTkButton(
            controls_frame,
            text="Start Recording",
            command=self.toggle_recording,
            width=150,
            height=50,
            state="disabled",
        )
        self.record_button.pack(side="left", padx=10, pady=10)

        # Recording time
        self.time_label = ctk.CTkLabel(
            controls_frame,
            textvariable=self.recording_time_var,
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        self.time_label.pack(side="left", padx=20, pady=10)

        # Next question button
        self.next_button = ctk.CTkButton(
            controls_frame,
            text="Next Question",
            command=self.next_question,
            width=150,
            state="disabled",
        )
        self.next_button.pack(side="left", padx=10, pady=10)

        # End interview button
        self.end_button = ctk.CTkButton(
            controls_frame,
            text="End Interview",
            command=self.end_interview,
            width=150,
            state="disabled",
            fg_color="red",
            hover_color="darkred",
        )
        self.end_button.pack(side="left", padx=10, pady=10)

        # Status frame
        status_frame = ctk.CTkFrame(self.interview_frame)
        status_frame.pack(fill="x", padx=10, pady=10)

        self.status_label = ctk.CTkLabel(
            status_frame, textvariable=self.status_var, font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(padx=10, pady=5)

        # Progress frame
        progress_frame = ctk.CTkFrame(self.interview_frame)
        progress_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(progress_frame, text="Progress:").pack(
            side="left", padx=10, pady=5
        )

        self.progress_bar = ctk.CTkProgressBar(progress_frame, width=400)
        self.progress_bar.pack(side="left", padx=10, pady=5)
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(progress_frame, text="0/10")
        self.progress_label.pack(side="left", padx=10, pady=5)

        # Analysis frame
        analysis_frame = ctk.CTkFrame(self.interview_frame)
        analysis_frame.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            analysis_frame,
            text="Response Analysis:",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=10, pady=5)

        self.analysis_text = ctk.CTkTextbox(
            analysis_frame, height=150, state="disabled"
        )
        self.analysis_text.pack(fill="both", expand=True, padx=10, pady=5)

        # Initially hide interview frame
        self.interview_frame.pack_forget()

    def start_interview(self):
        """Start the interview process"""
        job_title = self.job_title_var.get().strip()
        candidate_id = self.candidate_id_var.get().strip()
        job_description = self.job_description_text.get("1.0", "end").strip()

        if not job_title or not candidate_id or not job_description:
            messagebox.showerror("Error", "Please fill in all fields")
            return

        # Create session
        session_id = self.agent.create_interview_session(
            job_title, job_description, candidate_id
        )

        # Start interview
        if self.agent.start_interview(session_id):
            # Show interview frame
            self.interview_frame.pack(fill="both", expand=True, pady=(0, 20))

            # Enable controls
            self.record_button.configure(state="normal")
            self.end_button.configure(state="normal")

            # Get first question
            self.next_question()

            self.status_var.set(
                "Interview started. Click 'Start Recording' when ready to answer."
            )
        else:
            messagebox.showerror("Error", "Failed to start interview")

    def next_question(self):
        """Get the next question"""
        question = self.agent.get_next_question()

        if question:
            self.current_question_var.set(question.text)
            self.question_label.configure(text=question.text)

            # Convert question to speech
            self.agent.text_to_speech(question.text)

            # Update progress
            progress = self.agent.get_session_progress()
            self.progress_bar.set(progress["questions_asked"] / 10)
            self.progress_label.configure(text=f"{progress['questions_asked']}/10")

            # Reset recording state
            self.record_button.configure(text="Start Recording", state="normal")
            self.recording_time_var.set("00:00")

            # Clear analysis
            self.analysis_text.configure(state="normal")
            self.analysis_text.delete("1.0", "end")
            self.analysis_text.configure(state="disabled")

            self.status_var.set(
                "New question loaded. Click 'Start Recording' when ready to answer."
            )
        else:
            self.status_var.set("No more questions available.")

    def toggle_recording(self):
        """Toggle recording state"""
        if self.agent.is_recording:
            # Stop recording
            self.stop_recording()
        else:
            # Start recording
            self.start_recording()

    def start_recording(self):
        """Start recording audio"""
        if self.agent.start_recording():
            self.agent.is_recording = True
            self.record_button.configure(text="Stop Recording", fg_color="red")
            self.recording_start_time = time.time()
            self.update_recording_time()
            self.status_var.set("Recording... Click 'Stop Recording' when finished.")

    def stop_recording(self):
        """Stop recording and analyze response"""
        self.record_button.configure(text="Analyzing...", state="disabled")
        self.status_var.set("Analyzing response...")

        # Stop recording and analyze in separate thread
        def analyze():
            result = self.agent.stop_recording_and_analyze()

            # Update GUI in main thread
            self.root.after(0, self.process_analysis_result, result)

        thread = threading.Thread(target=analyze)
        thread.daemon = True
        thread.start()

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

            # Reset recording button
            self.record_button.configure(text="Start Recording", state="normal")

            # Check if interview should end
            if self.agent.should_end_interview():
                self.status_var.set(
                    "Interview complete. Click 'End Interview' to generate report."
                )
                self.record_button.configure(state="disabled")
                self.next_button.configure(state="disabled")
            else:
                self.status_var.set(
                    "Response analyzed. Click 'Next Question' to continue."
                )
                self.next_button.configure(state="normal")
        else:
            self.status_var.set("Error analyzing response. Please try again.")
            self.record_button.configure(text="Start Recording", state="normal")

    def update_recording_time(self):
        """Update recording time display"""
        if self.agent.is_recording and self.recording_start_time:
            elapsed = int(time.time() - self.recording_start_time)
            minutes = elapsed // 60
            seconds = elapsed % 60
            self.recording_time_var.set(f"{minutes:02d}:{seconds:02d}")

            # Schedule next update
            self.recording_timer = self.root.after(1000, self.update_recording_time)

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
                self.root.after(0, self.interview_ended, success)

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
        # Clear input fields
        self.job_title_var.set("")
        self.candidate_id_var.set("")
        self.job_description_text.delete("1.0", "end")

        # Hide interview frame
        self.interview_frame.pack_forget()

        # Reset variables
        self.current_question_var.set("")
        self.recording_time_var.set("00:00")
        self.status_var.set("Ready to start")

        # Reset progress
        self.progress_bar.set(0)
        self.progress_label.configure(text="0/10")

        # Clear analysis
        self.analysis_text.configure(state="normal")
        self.analysis_text.delete("1.0", "end")
        self.analysis_text.configure(state="disabled")

    def run(self):
        """Run the GUI application"""
        self.root.mainloop()


def main():
    """Main function to run the mock interview system"""
    app = MockInterviewGUI()
    app.run()


if __name__ == "__main__":
    main()
