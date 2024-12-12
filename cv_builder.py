from cat.experimental.form import form, CatForm
from pydantic import BaseModel, Field, field_validator, HttpUrl
from typing import List, Optional
from jinja2 import Environment, FileSystemLoader

from cat.log import log

from xhtml2pdf import pisa
import base64
import os
from io import BytesIO


class CV(BaseModel):
    full_name: str = Field(..., description="Full name of the individual")
    email: str = Field(..., description="Email address of the individual")
    phone_number: Optional[str] = Field(None, description="Phone number in international format (e.g., +123456789)")
    linkedIn_profile: Optional[HttpUrl] = Field(None, description="URL to the individual's LinkedIn profile")
    portfolio_website: Optional[HttpUrl] = Field(None, description="URL to the individual's personal portfolio website")
    summary: str = Field(..., description="A brief summary or objective of the individual")
    skills: List[str] = Field(..., description="A list of skills relevant to the job")
    experience: List[dict] = Field(
        ...,
        description="A list of work experiences. Each entry contains keys: 'job_title', 'company_name', 'start_date', 'end_date', and 'description'"
    )
    education: List[dict] = Field(
        ...,
        description="A list of education details. Each entry contains keys: 'institution_name', 'degree', 'field_of_study', 'start_date', 'end_date', and 'description'"
    )
    # certifications: Optional[List[dict]] = Field(
    #     None,
    #     description="A list of certifications. Each entry contains keys: 'name', 'issuing_organization', 'issue_date', and 'expiration_date'"
    # )
    # languages: Optional[List[str]] = Field(None, description="A list of languages known")
    # hobbies: Optional[List[str]] = Field(None, description="A list of hobbies or interests")

    # Validators
    @field_validator("skills")
    @classmethod
    def validate_skills(cls, value: List[str]) -> List[str]:
        if not value:
            raise ValueError("Skills list cannot be empty")
        return value

    @field_validator("experience")
    @classmethod
    def validate_experience(cls, value: List[dict]) -> List[dict]:
        for item in value:
            required_keys = {"job_title", "company_name", "start_date", "end_date", "description"}
            if not all(key in item for key in required_keys):
                raise ValueError(f"Each experience entry must contain the following keys: {', '.join(required_keys)}")
        return value

    @field_validator("education")
    @classmethod
    def validate_education(cls, value: List[dict]) -> List[dict]:
        for item in value:
            required_keys = {"institution_name", "degree", "field_of_study", "start_date", "end_date", "description"}
            if not all(key in item for key in required_keys):
                raise ValueError(f"Each education entry must contain the following keys: {', '.join(required_keys)}")
        return value



@form
class CVForm(CatForm):
    description = "CV Builder"
    model_class = CV
    start_examples = [
        "I want to build my resume",
        "I want a resume",
        "I want a CV",
    ]
    stop_examples = [
        "I don't want to build my resume",
        "I don't want a resume",
        "I don't want a CV"
    ]
    # Ask for confirmation before finalizing
    ask_confirm = True

    # Jinja2 setup for rendering the CV template
    template_env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "default_templates")))
    template_file = "template_001.html"

    # Method to handle form submission
    def submit(self, form_data):
        # Render the Jinja2 template with the collected form data
        try:
            log.debug("Generating CV...")
            template = self.template_env.get_template(self.template_file)
            rendered_cv = template.render(form_data)

            # Convert HTML to PDF using xhtml2pdf
            pdf_stream = BytesIO()
            pisa.CreatePDF(BytesIO(rendered_cv.encode('utf-8')), dest=pdf_stream)
            pdf_stream.seek(0)

            # Encode PDF to Base64
            encoded_pdf = base64.b64encode(pdf_stream.read()).decode('utf-8')

            return {
                "output": f"<a href='data:application/pdf;base64,{encoded_pdf}' download='cv.pdf'>Download CV</a>"
            }
        except Exception as e:
            log.error(f"An error occurred while generating your CV: {e}")
            return {
                "output": f"An error occurred while generating your CV: {e}"
            }

    # Handle the situation where the user cancels the form
    def message_closed(self):
        prompt = (
            "The customer no longer wants to build their CV. Respond with a short, professional acknowledgment."
        )
        return {"output": self.cat.llm(prompt)}

    # Generate a confirmation message for user approval
    def message_wait_confirm(self):
        prompt = (
            "Summarize the collected details of the CV briefly and clearly:\n"
            f"{self._generate_base_message()}\n"
            "Say something like, 'Here’s what we’ve put together for your CV. Do you want to finalize it?'"
        )
        return {"output": f"{self.cat.llm(prompt)}"}

    # Handle incomplete form inputs with a professional nudge
    def message_incomplete(self):
        prompt = (
            f"The CV form is missing some critical details:\n{self._generate_base_message()}\n"
            "Craft a professional nudge to encourage completion. For example, if 'work experience' is missing, say: "
            "'Please provide details of your past work experience to enhance your resume.'"
        )
        return {"output": f"{self.cat.llm(prompt)}"}

