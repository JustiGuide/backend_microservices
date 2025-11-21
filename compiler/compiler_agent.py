import base64
import io
import json
from typing import List, Dict, Union, Any
from urllib.parse import urlparse
import PyPDF2
from docx import Document
from openai import OpenAI
from pdf2image import convert_from_bytes
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from response_schemas import (
    RequiredDocuments,
    FileClassification,
    FILE_CLASSIFICATION_SCHEMA,
    DocumentValidation,
    DOC_VALIDATION_SCHEMA,
)
from documents_gateway import DocumentsGateway

docs = DocumentsGateway()

load_dotenv()

class Compiler:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.MASTER_LIST = [
            {
                "form_name": "i589",
                "is_supplement": False,
                "supplement_name": None,
                "document_list": [
                    {
                        "document_name": "I-589 Filing Fee",
                        "description": "The required filing fee for Form I-589, Application for Asylum and for Withholding of Removal. (Currently, there is no fee for asylum applications, but this may change.)",
                        "conditions": [
                            "Required if a fee is instituted by USCIS in the future. Currently, no fee is required for asylum applications."
                        ],
                        "checks": [
                            "Check current USCIS instructions to confirm no fee is required.",
                            "If a fee is required, ensure payment is for the correct amount and payable to 'U.S. Department of Homeland Security'.",
                        ],
                    },
                    {
                        "document_name": "Passport or National Identity Document",
                        "description": "A copy of your passport identity page or, if unavailable, a national identity document with your photo and/or fingerprint.",
                        "conditions": ["Required for all I-589 applicants."],
                        "checks": [
                            "Document is clear and legible.",
                            "Photo, name, and date of birth are visible.",
                            "If unavailable, provide a written explanation.",
                        ],
                    },
                    {
                        "document_name": "Form I-94 Arrival/Departure Record",
                        "description": "A copy of your most recent Form I-94, if you were admitted to the United States.",
                        "conditions": [
                            "Required if you were lawfully admitted to the U.S."
                        ],
                        "checks": [
                            "I-94 shows your name, date of entry, and class of admission.",
                            "If not available, provide a written explanation.",
                        ],
                    },
                    {
                        "document_name": "Personal Statement",
                        "description": "A detailed written statement describing the reasons you are seeking asylum, including past persecution or fear of future persecution.",
                        "conditions": ["Required for all I-589 applicants."],
                        "checks": [
                            "Statement is detailed and addresses all relevant facts.",
                            "Explains the basis for asylum claim (race, religion, nationality, political opinion, or membership in a particular social group).",
                        ],
                    },
                    {
                        "document_name": "Supporting Evidence of Persecution or Harm",
                        "description": "Any documents supporting your claim, such as police reports, medical records, affidavits, news articles, or country condition reports.",
                        "conditions": [
                            "Required if available. Strongly recommended for all applicants."
                        ],
                        "checks": [
                            "Documents are relevant and support the facts in your personal statement.",
                            "Translations are provided for all non-English documents, with a certificate of translation.",
                        ],
                    },
                    {
                        "document_name": "Birth Certificate or Other Identity Documents",
                        "description": "A copy of your birth certificate or other official identity documents.",
                        "conditions": ["Required for all I-589 applicants."],
                        "checks": [
                            "Document is legible and includes your name and date of birth.",
                            "If unavailable, provide a written explanation.",
                        ],
                    },
                    {
                        "document_name": "Marriage Certificate (if applicable)",
                        "description": "A copy of your marriage certificate if you are married.",
                        "conditions": [
                            "Required if you are married and including your spouse in the application."
                        ],
                        "checks": [
                            "Certificate is legible and officially issued.",
                            "If not in English, a certified translation is attached.",
                        ],
                    },
                    {
                        "document_name": "Children's Birth Certificates (if applicable)",
                        "description": "Copies of birth certificates for any children included in your application.",
                        "conditions": [
                            "Required if you are including children in your application."
                        ],
                        "checks": [
                            "Certificates are legible and officially issued.",
                            "If not in English, a certified translation is attached.",
                        ],
                    },
                    {
                        "document_name": "Evidence of Relationship to Spouse/Children (if applicable)",
                        "description": "Documents proving your relationship to your spouse and/or children (e.g., marriage certificate, birth certificates, adoption records).",
                        "conditions": [
                            "Required if you are including family members in your application."
                        ],
                        "checks": [
                            "Documents are official and legible.",
                            "If not in English, a certified translation is attached.",
                        ],
                    },
                    {
                        "document_name": "Two Passport-Style Photographs",
                        "description": "Two recent, identical, color passport-style photographs of yourself and each family member included in the application.",
                        "conditions": [
                            "Required for all I-589 applicants and each included family member."
                        ],
                        "checks": [
                            "Photos are 2x2 inches, taken within the last 30 days.",
                            "White or off-white background, full-face view, neutral expression.",
                        ],
                    },
                ],
            },
            {
                "form_name": "i129",
                "is_supplement": False,
                "supplement_name": None,
                "document_list": [
                    {
                        "document_name": "I-129 Filing Fee",
                        "description": "The required filing fee for Form I-129, Petition for a Nonimmigrant Worker.",
                        "conditions": [
                            "Required for all I-129 petitions unless a specific fee waiver is granted."
                        ],
                        "checks": [
                            "Check is for the correct, current amount as per the USCIS website.",
                            "Payable to 'U.S. Department of Homeland Security'.",
                            "Petitioner's name and form number are written on the check's memo line.",
                        ],
                    },
                    {
                        "document_name": "Employer Support Letter",
                        "description": "A letter from the petitioning employer detailing the job offer, duties, salary, and the beneficiary's qualifications for the position.",
                        "conditions": ["Required for all I-129 petitions."],
                        "checks": [
                            "Printed on company letterhead.",
                            "Signed by an authorized representative.",
                            "Includes job title, detailed duties, salary, and required qualifications.",
                            "Confirms the beneficiary's qualifications match the role.",
                        ],
                    },
                    {
                        "document_name": "Employer's Ability to Pay",
                        "description": "Evidence demonstrating the employer's financial capacity to pay the proffered wage, such as annual reports, federal tax returns, or audited financial statements.",
                        "conditions": ["Required for all I-129 petitions."],
                        "checks": [
                            "Financial documents are recent and relevant.",
                            "Clearly shows assets, net income, and net current assets sufficient to cover the beneficiary's salary.",
                        ],
                    },
                    {
                        "document_name": "Beneficiary's Qualifications",
                        "description": "Evidence of the beneficiary's educational and professional qualifications, such as diplomas, transcripts, and letters of experience from previous employers.",
                        "conditions": ["Required for all I-129 petitions."],
                        "checks": [
                            "Diplomas/transcripts are from accredited institutions.",
                            "If a foreign degree, an educational equivalency evaluation is included.",
                            "Experience letters detail job duties, dates of employment, and are on company letterhead.",
                        ],
                    },
                    {
                        "document_name": "Beneficiary's Passport",
                        "description": "A clear, legible copy of the beneficiary's passport identity page.",
                        "conditions": ["Required for all I-129 petitions."],
                        "checks": [
                            "Passport is valid and not expired.",
                            "Shows the beneficiary's photo, name, and date of birth clearly.",
                        ],
                    },
                    {
                        "document_name": "Beneficiary's Form I-94",
                        "description": "A copy of the beneficiary's most recent Form I-94 Arrival/Departure Record.",
                        "conditions": [
                            "Required if the beneficiary is currently in the United States."
                        ],
                        "checks": [
                            "Shows the beneficiary's current nonimmigrant status.",
                            "Confirms admission to the U.S. and authorized period of stay.",
                        ],
                    },
                ],
            },
            {
                "form_name": "i129",
                "is_supplement": True,
                "supplement_name": "H-1B Classification",
                "document_list": [
                    {
                        "document_name": "Certified Labor Condition Application (LCA)",
                        "description": "A certified Form ETA-9035, Labor Condition Application for Nonimmigrant Workers, from the U.S. Department of Labor.",
                        "conditions": ["Required for all H-1B petitions."],
                        "checks": [
                            "LCA is certified by the Department of Labor.",
                            "Corresponds to the specific job, location, and wage offered in the petition.",
                            "Validity dates cover the requested period of employment.",
                        ],
                    },
                    {
                        "document_name": "Specialty Occupation Evidence",
                        "description": "Evidence demonstrating that the position qualifies as a specialty occupation, which normally requires a bachelor's or higher degree in a specific field.",
                        "conditions": ["Required for all H-1B petitions."],
                        "checks": [
                            "Job descriptions from O*NET or other industry sources.",
                            "Evidence of past hiring practices for the role.",
                            "Expert opinion letters.",
                            "Detailed explanation of how the degree relates to the complex duties of the job.",
                        ],
                    },
                    {
                        "document_name": "State License",
                        "description": "Copies of any required state or local license, registration, or certification that allows the beneficiary to practice the specialty occupation.",
                        "conditions": [
                            "Required if the specialty occupation legally requires a license to practice in the state of intended employment."
                        ],
                        "checks": [
                            "License is current and valid.",
                            "Issued by the appropriate state or local authority.",
                            "Beneficiary's name is clearly listed.",
                        ],
                    },
                    {
                        "document_name": "Petitioner-Beneficiary Contract",
                        "description": "A copy of any written contract between the petitioner (employer) and the beneficiary (employee).",
                        "conditions": ["Required if a written contract exists."],
                        "checks": [
                            "Signed by both parties.",
                            "Terms and conditions are clearly stated.",
                        ],
                    },
                ],
            },
            {
                "form_name": "i129",
                "is_supplement": True,
                "supplement_name": "H-2B Classification (Temporary Non-Agricultural Worker)",
                "document_list": [
                    {
                        "document_name": "Temporary Labor Certification (TLC)",
                        "description": "An approved Temporary Labor Certification from the U.S. Department of Labor.",
                        "conditions": ["Required for all H-2B petitions."],
                        "checks": [
                            "Certification is approved and not expired.",
                            "Name of the petitioner matches the I-129 form.",
                            "Job opportunity and number of workers match the petition.",
                        ],
                    },
                    {
                        "document_name": "Proof of Temporary Need",
                        "description": "Evidence proving the employer's need for the worker is temporary, such as seasonal, peak load, one-time occurrence, or intermittent.",
                        "conditions": ["Required for all H-2B petitions."],
                        "checks": [
                            "Clearly explains why the need is temporary and not permanent.",
                            "Supported by documents like charts, historical payroll data, contracts, or project timelines.",
                        ],
                    },
                    {
                        "document_name": "Beneficiary's U.S. Employment History",
                        "description": "Copies of the beneficiary's pay stubs and Form I-94.",
                        "conditions": [
                            "Required if the beneficiary is already in the U.S."
                        ],
                        "checks": [
                            "Includes recent pay stubs from U.S. employer.",
                            "Copy of Form I-94 is legible and current.",
                        ],
                    },
                ],
            },
            {
                "form_name": "i129",
                "is_supplement": True,
                "supplement_name": "L-1 Classification (Intracompany Transferee)",
                "document_list": [
                    {
                        "document_name": "Proof of Qualifying Corporate Relationship",
                        "description": "Evidence showing the qualifying relationship between the U.S. and foreign company (e.g., parent, subsidiary, branch, or affiliate).",
                        "conditions": ["Required for all L-1 petitions."],
                        "checks": [
                            "Includes documents like articles of incorporation, stock certificates, annual reports, or partnership agreements.",
                            "Clearly establishes the corporate structure and ownership.",
                        ],
                    },
                    {
                        "document_name": "Proof of Prior Foreign Employment",
                        "description": "Evidence that the beneficiary was employed by the foreign company for at least one continuous year in the preceding three years.",
                        "conditions": ["Required for all L-1 petitions."],
                        "checks": [
                            "Employment confirmation letters from the foreign entity.",
                            "Payroll records or tax documents proving the one year of employment.",
                            "Dates of employment are clearly stated.",
                        ],
                    },
                    {
                        "document_name": "Detailed U.S. Job Description (L-1)",
                        "description": "A detailed description of the beneficiary's proposed duties in the U.S. in a managerial, executive, or specialized knowledge capacity.",
                        "conditions": ["Required for all L-1 petitions."],
                        "checks": [
                            "Clearly specifies if the role is Managerial (L-1A), Executive (L-1A), or Specialized Knowledge (L-1B).",
                            "Includes organizational charts showing the beneficiary's position.",
                            "For specialized knowledge, explains why the knowledge is uncommon or advanced.",
                        ],
                    },
                ],
            },
            {
                "form_name": "i129",
                "is_supplement": True,
                "supplement_name": "O-1 Classification (Individuals with Extraordinary Ability or Achievement)",
                "document_list": [
                    {
                        "document_name": "O-1 Consultation Letter",
                        "description": "A written advisory opinion from a peer group, union, or a person/organization with expertise in the beneficiary's area of ability.",
                        "conditions": ["Required for all O-1 petitions."],
                        "checks": [
                            "From a relevant and recognized peer group or expert.",
                            "Describes the beneficiary's ability and the proposed work.",
                            "States 'no objection' or provides a detailed advisory opinion.",
                        ],
                    },
                    {
                        "document_name": "O-1 Contract",
                        "description": "A copy of the written contract between the petitioner and the beneficiary, or a summary of the terms of an oral agreement.",
                        "conditions": ["Required for all O-1 petitions."],
                        "checks": [
                            "If a written contract, it is signed by both parties.",
                            "If oral, the summary covers all material terms, including wages and duties.",
                        ],
                    },
                    {
                        "document_name": "O-1 Itinerary",
                        "description": "A detailed itinerary of events, activities, or performances.",
                        "conditions": [
                            "Required if the beneficiary will work in multiple locations or for multiple employers (via an agent petitioner)."
                        ],
                        "checks": [
                            "Includes dates, locations, and descriptions of each engagement.",
                            "Corresponds with contracts or other supporting evidence.",
                        ],
                    },
                    {
                        "document_name": "Evidence of Extraordinary Ability",
                        "description": "Extensive evidence proving the beneficiary's extraordinary ability, such as a major award (e.g., Nobel, Oscar) or at least three other forms of evidence.",
                        "conditions": ["Required for all O-1 petitions."],
                        "checks": [
                            "Evidence meets the high standard for the O-1 category.",
                            "Examples include nationally/internationally recognized awards, high salary, publications about the beneficiary, leading role in distinguished organizations, etc.",
                        ],
                    },
                ],
            },
            {
                "form_name": "i130",
                "is_supplement": False,
                "supplement_name": None,
                "document_list": [
                    {
                        "document_name": "I-130 Filing Fee",
                        "description": "The required filing fee for Form I-130, Petition for Alien Relative.",
                        "conditions": ["Required for all I-130 petitions."],
                        "checks": [
                            "Check is for the correct, current amount as per the USCIS website.",
                            "Payable to 'U.S. Department of Homeland Security'.",
                        ],
                    },
                    {
                        "document_name": "Proof of Petitioner's Status",
                        "description": "Proof of the petitioner's U.S. citizenship or lawful permanent resident status.",
                        "conditions": ["Required for all I-130 petitions."],
                        "checks": [
                            "For U.S. Citizen: U.S. birth certificate, U.S. passport, naturalization certificate, or certificate of citizenship.",
                            "For LPR: Copy of Green Card (front and back).",
                        ],
                    },
                    {
                        "document_name": "Proof of Qualifying Relationship",
                        "description": "Documents proving the family relationship between the petitioner and the beneficiary.",
                        "conditions": ["Required for all I-130 petitions."],
                        "checks": [
                            "For spouse: Marriage certificate.",
                            "For child: Child's birth certificate showing petitioner as parent.",
                            "For parent: Petitioner's birth certificate showing beneficiary as parent.",
                        ],
                    },
                    {
                        "document_name": "Evidence of Bona Fide Marriage",
                        "description": "Evidence showing that the marriage is genuine and not for immigration purposes.",
                        "conditions": ["Required if the petition is for a spouse."],
                        "checks": [
                            "Joint documents: leases, bank account statements, tax returns, insurance policies.",
                            "Photos together over the course of the relationship.",
                            "Birth certificates of children born to the petitioner and beneficiary.",
                            "Affidavits from friends and family.",
                        ],
                    },
                    {
                        "document_name": "Proof of Prior Marriage Termination",
                        "description": "Legal proof of the termination of any previous marriages for both the petitioner and beneficiary.",
                        "conditions": [
                            "Required if either the petitioner or beneficiary was previously married."
                        ],
                        "checks": [
                            "Final divorce decrees.",
                            "Death certificates.",
                            "Annulment documents.",
                        ],
                    },
                ],
            },
            {
                "form_name": "i765",
                "is_supplement": False,
                "supplement_name": None,
                "document_list": [
                    {
                        "document_name": "I-765 Filing Fee",
                        "description": "The filing fee for Form I-765 or a completed Form I-912, Request for Fee Waiver.",
                        "conditions": [
                            "Required unless applying under a category exempt from fees or a fee waiver is approved."
                        ],
                        "checks": [
                            "Check is for the correct, current amount per USCIS instructions.",
                            "Payable to 'U.S. Department of Homeland Security'.",
                            "If requesting a waiver, Form I-912 is complete and includes required proof.",
                        ],
                    },
                    {
                        "document_name": "Applicant's Form I-94",
                        "description": "A copy of the applicant's Form I-94 Arrival/Departure Record.",
                        "conditions": [
                            "Required if the applicant was lawfully admitted to the U.S."
                        ],
                        "checks": [
                            "Shows applicant's name, date of entry, and class of admission.",
                            "Can be obtained from the CBP website.",
                        ],
                    },
                    {
                        "document_name": "Previous Employment Authorization Document (EAD)",
                        "description": "A copy of the applicant's last EAD, if any.",
                        "conditions": [
                            "Required if the applicant was previously issued an EAD."
                        ],
                        "checks": [
                            "Copy includes both front and back.",
                            "Applicant's name and A-Number are legible.",
                        ],
                    },
                    {
                        "document_name": "Passport-Style Photographs",
                        "description": "Two identical 2x2 inch passport-style color photographs taken within the last 30 days.",
                        "conditions": ["Required for all paper-based I-765 filings."],
                        "checks": [
                            "White to off-white background.",
                            "Full-face view, neutral expression.",
                            "Applicant's name and A-Number (if any) lightly written in pencil on the back.",
                        ],
                    },
                    {
                        "document_name": "Government-Issued Photo ID",
                        "description": "A copy of a government-issued photo identification document, such as a passport identity page.",
                        "conditions": ["Required for all I-765 filings."],
                        "checks": [
                            "Document is not expired.",
                            "Photo, name, and date of birth are clear and legible.",
                        ],
                    },
                ],
            },
            {
                "form_name": "i765",
                "is_supplement": True,
                "supplement_name": "Based on Pending Asylum Application (c)(8)",
                "document_list": [
                    {
                        "document_name": "Proof of Pending Asylum Application",
                        "description": "Evidence that your Form I-589 has been pending for at least 150 days (the 'asylum clock').",
                        "conditions": [
                            "Required when applying for an EAD based on a pending asylum case under category (c)(8)."
                        ],
                        "checks": [
                            "A copy of the Form I-797C, Notice of Action, for the I-589.",
                            "Any other notices from USCIS or the Immigration Court related to the asylum application.",
                        ],
                    }
                ],
            },
            {
                "form_name": "i765",
                "is_supplement": True,
                "supplement_name": "Asylee (a)(5)",
                "document_list": [
                    {
                        "document_name": "Asylum Grant Letter",
                        "description": "A copy of the letter or immigration judge's order granting asylum.",
                        "conditions": [
                            "Required when applying for an EAD as a granted asylee under category (a)(5)."
                        ],
                        "checks": [
                            "Letter is from a USCIS asylum office or an order from an Immigration Judge.",
                            "Clearly states that asylum has been granted.",
                        ],
                    }
                ],
            },
            {
                "form_name": "i765",
                "is_supplement": True,
                "supplement_name": "F-1 Student Seeking Optional Practical Training (OPT) (c)(3)(B)",
                "document_list": [
                    {
                        "document_name": "OPT-Endorsed Form I-20",
                        "description": "A copy of the Form I-20, Certificate of Eligibility for Nonimmigrant Student Status, endorsed for OPT by the Designated School Official (DSO).",
                        "conditions": [
                            "Required when applying for an EAD based on F-1 OPT under category (c)(3)(B)."
                        ],
                        "checks": [
                            "DSO signature and OPT recommendation are present and dated within the last 30 days.",
                            "Applicant's signature is on the form.",
                            "All pages of the I-20 are included.",
                        ],
                    }
                ],
            },
            {
                "form_name": "i765",
                "is_supplement": True,
                "supplement_name": "Adjustment of Status Applicant (c)(9)",
                "document_list": [
                    {
                        "document_name": "I-485 Receipt Notice",
                        "description": "A copy of Form I-797C, Notice of Action, showing that your Form I-485, Application to Register Permanent Residence or Adjust Status, is pending.",
                        "conditions": [
                            "Required when applying for an EAD based on a pending I-485 under category (c)(9)."
                        ],
                        "checks": [
                            "Receipt number is clearly visible.",
                            "Applicant's name is correct.",
                            "Notice shows the I-485 case is currently pending.",
                        ],
                    }
                ],
            },
            {
                "form_name": "i765",
                "is_supplement": True,
                "supplement_name": "Spouse of an H-1B Nonimmigrant (c)(26)",
                "document_list": [
                    {
                        "document_name": "Proof of H-4 Status",
                        "description": "Evidence of your current H-4 status, such as a copy of your Form I-94 and Form I-797 approval notice.",
                        "conditions": ["Required for H-4 spouse EAD applications."],
                        "checks": [
                            "I-94 shows H-4 as the class of admission.",
                            "I-797 approval notice is for your most recent H-4 status.",
                        ],
                    },
                    {
                        "document_name": "Spouse's H-1B Status",
                        "description": "Evidence of your spouse's current H-1B status, including their I-94, I-797 approval notice, and passport.",
                        "conditions": ["Required for H-4 spouse EAD applications."],
                        "checks": [
                            "Spouse's documents confirm they are maintaining H-1B status."
                        ],
                    },
                    {
                        "document_name": "Marriage Certificate",
                        "description": "A copy of your marriage certificate to the H-1B principal.",
                        "conditions": ["Required for H-4 spouse EAD applications."],
                        "checks": [
                            "Legible and includes names of both spouses.",
                            "If not in English, a certified English translation is required.",
                        ],
                    },
                    {
                        "document_name": "Proof of EAD Eligibility via H-1B Spouse",
                        "description": "Evidence that your H-1B spouse is the beneficiary of an approved Form I-140, or has been granted an H-1B extension beyond the six-year limit under AC21.",
                        "conditions": ["Required for H-4 spouse EAD applications."],
                        "checks": [
                            "Copy of the I-140 approval notice (Form I-797).",
                            "Or, evidence of H-1B status approved beyond the 6-year maximum.",
                        ],
                    },
                ],
            },
            {
                "form_name": "n400",
                "is_supplement": False,
                "supplement_name": None,
                "document_list": [
                    {
                        "document_name": "N-400 Filing Fee or Fee Waiver Application",
                        "description": "The required filing fee for Form N-400, Application for Naturalization, or a Form I-912 fee waiver application with supporting documentation.",
                        "conditions": [
                            "Required for all N-400 applications. Either the filing fee or an approved fee waiver is necessary."
                        ],
                        "checks": [
                            "For filing fee: Check is for the correct, current amount per USCIS website.",
                            "For filing fee: Payable to 'U.S. Department of Homeland Security'.",
                            "For fee waiver: Form I-912 is complete and signed.",
                            "For fee waiver: Supporting documentation of financial hardship is included (tax returns, proof of public benefits, etc.).",
                            "For fee waiver: Income is at or below 150% of Federal Poverty Guidelines or there's evidence of financial hardship.",
                        ],
                    },
                    {
                        "document_name": "Copy of Permanent Resident Card",
                        "description": "A copy of both the front and back of your Form I-551, Permanent Resident Card (Green Card).",
                        "conditions": ["Required for all N-400 applicants."],
                        "checks": [
                            "Copy is clear and legible.",
                            "Card is not expired, or if expired, a copy of the I-797 receipt for the I-90 renewal is included.",
                        ],
                    },
                    {
                        "document_name": "Current Marriage Certificate",
                        "description": "A copy of your current legal marriage certificate.",
                        "conditions": ["Required if you are currently married."],
                        "checks": [
                            "Document is legible and officially issued.",
                            "If not in English, a certified English translation is attached.",
                        ],
                    },
                    {
                        "document_name": "Proof of Prior Marriage(s) Termination",
                        "description": "Divorce decrees, annulment records, or death certificates for all prior marriages for both you and your current spouse.",
                        "conditions": [
                            "Required if you or your current spouse were previously married."
                        ],
                        "checks": [
                            "Documents are final and legally binding.",
                            "Covers every prior marriage listed on the application.",
                        ],
                    },
                    {
                        "document_name": "Evidence of Legal Name Change",
                        "description": "A copy of the court order or other legal document showing your name change.",
                        "conditions": [
                            "Required if you have used any name other than what is on your Green Card."
                        ],
                        "checks": [
                            "Copy of marriage certificate, divorce decree, or court order is included."
                        ],
                    },
                    {
                        "document_name": "Tax Returns or IRS Transcript",
                        "description": "Copies of your federal income tax returns or an IRS tax transcript for the required statutory period.",
                        "conditions": [
                            "Required for all N-400 applicants to prove good moral character and physical presence."
                        ],
                        "checks": [
                            "Covers the last 5 years (or 3 years if applying based on marriage to a U.S. citizen).",
                            "If you did not file taxes, include a signed explanation.",
                        ],
                    },
                    {
                        "document_name": "Evidence for Marriage-Based Application",
                        "description": "Evidence of your spouse's U.S. citizenship for the past 3 years and proof of your marital union.",
                        "conditions": [
                            "Required if applying based on 3 years of marriage to a U.S. citizen."
                        ],
                        "checks": [
                            "Spouse's birth certificate, passport, or naturalization certificate.",
                            "Joint bank accounts, leases, mortgages, and birth certificates of children.",
                        ],
                    },
                    {
                        "document_name": "Proof of Selective Service Registration",
                        "description": "Your registration acknowledgement card from the Selective Service System.",
                        "conditions": [
                            "Required for male applicants who lived in the U.S. between the ages of 18 and 26."
                        ],
                        "checks": [
                            "Proof of registration can be obtained from the SSS.gov website.",
                            "If you failed to register, a detailed explanation and a status information letter are required.",
                        ],
                    },
                ],
            },
        ]

    def get_document_checklist_with_ai(
        self,
        form_name: str,
        form_values: Dict[str, Any],
    ) -> List[Dict[str, Any]]:

        relevant_master_list = [
            item for item in self.MASTER_LIST if item["form_name"] == form_name
        ]
        if not relevant_master_list:
            return []

        REQUIRED_DOCS_SCHEMA = RequiredDocuments.model_json_schema()

        prompt = self._create_checklist_prompt(
            relevant_master_list, form_name, form_values
        )

        tool_name = "create_document_checklist"
        tools = [
            {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": "Creates the final list of required document objects.",
                    "parameters": REQUIRED_DOCS_SCHEMA,
                },
            }
        ]

        try:
            response = self.client.chat.completions.create(
                model="o3",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert paralegal specializing in U.S. immigration. Your task is to analyze a user's case details and a master list of possible documents. Based on the user's details, you will create a final checklist by selecting the relevant documents and returning a list of the *complete document dictionary objects* for all required documents.",
                    },
                    {"role": "user", "content": prompt},
                ],
                tool_choice={"type": "function", "function": {"name": tool_name}},
                tools=tools,
            )
            tool_calls = response.choices[0].message.tool_calls

            if tool_calls:
                function_args = json.loads(tool_calls[0].function.arguments)
                validated_data = RequiredDocuments(**function_args)

                unique_docs = []
                seen_names = set()
                for doc_item in validated_data.document_list:
                    if doc_item.document_name not in seen_names:
                        unique_docs.append(doc_item.model_dump())
                        seen_names.add(doc_item.document_name)

                return unique_docs

        except Exception as e:
            return [
                {
                    "document_name": "Error",
                    "description": f"An error occurred during AI checklist generation: {e}",
                    "conditions": [],
                    "checks": ["Please try again or contact support."],
                }
            ]

        return []

    def _create_checklist_prompt(
        self, relevant_list: List, form_name: str, form_values: Dict
    ) -> str:
        return f"""
        I am preparing an immigration application for Form {form_name}.
        Here is the master list of all possible required documents:
        ---
        MASTER DOCUMENT LIST:
        {json.dumps(relevant_list, indent=2)}
        ---
        Here are the user's case details:
        ---
        USER'S CASE DETAILS:
        {json.dumps(form_values, indent=2)}
        ---
        Based on the user's case details, compile a final, single, flat list of all required documents. Do not include duplicates or placeholder text.
        Provide your final answer using the `create_document_checklist` tool.
        """

    def analyze_and_validate_documents(
        self,
        document_checklist: List[Dict[str, Any]],
        file_details_list: List[Dict[str, Union[str, bytes]]],
    ) -> List[Dict[str, str]]:
        matches = {}
        for file_details in file_details_list:
            # print(f"Analyzing file: {file_details.get('filename', 'Unknown')}")
            classification = self._classify_file_with_ai(
                file_details, document_checklist
            )

            if classification and classification.best_match != "None":
                if (
                    classification.best_match not in matches
                    or classification.confidence_score
                    > matches[classification.best_match]["confidence"]
                ):
                    matches[classification.best_match] = {
                        "file_details": file_details,
                        "confidence": classification.confidence_score,
                    }

        # print(f"Finished classification. Found {len(matches)} matches.")

        final_status_report = []
        for doc_definition in document_checklist:
            # print(f"Verifiying document: {doc_definition['document_name']}")
            doc_name = doc_definition["document_name"]

            # Check if we found a matching file for this required document.
            if doc_name in matches:
                matched_file = matches[doc_name]["file_details"]

                # 4. Perform deep validation using the full document definition.
                # This is the key change: we pass the entire `doc_definition` dictionary,
                # which contains the `checks` list for the validation function to use.
                validation_result = self.validate_and_verify_document(
                    matched_file, doc_definition
                )

                status = "Present" if validation_result["is_valid"] else "Replace"

                final_status_report.append(
                    {
                        "document_name": doc_name,
                        "description": doc_definition[
                            "description"
                        ],  # Include the description in the report
                        "status": status,
                        "file_url": matched_file.get("file_url"),
                        "replace_reasons": (
                            ", ".join(validation_result["issues"])
                            if not validation_result["is_valid"]
                            else None
                        ),
                    }
                )
            else:
                # If no file was matched to this required document, mark it as "Missing".
                final_status_report.append(
                    {
                        "document_name": doc_name,
                        "description": doc_definition[
                            "description"
                        ],  # Also include description for missing items
                        "status": "Missing",
                        "file_url": None,
                        "replace_reasons": None,
                    }
                )
        # print("Document analysis complete. Generating final status report.")
        return final_status_report

    def _create_representative_snippet(
        self, text: str, length: int = 200, sections: int = 3
    ) -> str:
        if not text or len(text) < length * sections:
            return text
        start = text[:length]
        midpoint = len(text) // 2
        middle_start = max(len(start), midpoint - (length // 2))
        middle_end = middle_start + length
        middle = text[middle_start:middle_end]
        end_start = max(middle_end, len(text) - length)
        end = text[end_start:]
        return (
            f"{start}... (middle of document) ...{middle}... (end of document) ...{end}"
        )

    def _pdf_to_base64_images(self, pdf_bytes: bytes, dpi: int = 200) -> List[str]:
        """
        Converts each page of a PDF's byte content into a Base64 encoded PNG string.
        Includes the fix for the 'PA' mode error.
        """
        base64_images = []
        try:
            pil_images = convert_from_bytes(pdf_bytes, dpi=dpi)
            for image in pil_images:
                if image.mode == "PA" or image.mode == "P":
                    image = image.convert("RGBA")

                buffered = io.BytesIO()
                image.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                base64_images.append(img_str)
        except Exception as e:
            print(f"Error converting PDF bytes to images: {e}")
        return base64_images

    def _classify_file_with_ai(
        self, file_details: Dict, document_checklist: List[Dict[str, Any]]
    ) -> Union["FileClassification", None]:
        """
        Uses an AI model to classify a file against a structured list of possible documents.

        This version is updated to accept a list of document dictionaries. It provides
        the AI with richer context (names and descriptions) to improve classification accuracy.
        """
        filename = file_details.get("filename", "")
        content_type = file_details.get("content_type")
        messages = []
        model_to_use = "o3"  # Or your preferred model

        # Create a simplified list for the AI prompt (name + description)
        # This gives context without overwhelming the AI with unnecessary details for this step.
        checklist_for_prompt = [
            {
                "document_name": doc["document_name"],
                "description": doc["description"],
                "checks": doc["checks"],
            }
            for doc in document_checklist
        ]

        system_prompt = "You are a document classification expert. Your task is to identify what a given file is by matching it to a document from a provided list. The list contains document names and their descriptions. Use this context to make an accurate match. If the file does not confidently match any item, you MUST return 'None'."
        user_prompt_text = f'Analyze the following file. Which ONE of the following checklist items does it best match?\n\nDOCUMENT CHECKLIST:\n{json.dumps(checklist_for_prompt, indent=2)}\n\nFilename: "{filename}"\n\nUse the `classify_file` tool to provide your answer.'

        if content_type == "image":
            image_data = file_details.get("image_data")
            if not image_data:
                return None
            base64_image = base64.b64encode(image_data).decode("utf-8")
            messages = [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt_text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                },
            ]
        elif content_type == "pdf_images":
            pdf_bytes = file_details.get("image_data")
            if not pdf_bytes:
                return None
            base64_pages = self._pdf_to_base64_images(pdf_bytes)
            if not base64_pages:
                return None

            prompt_content = [{"type": "text", "text": user_prompt_text}]
            # Limit to the first 3 pages to manage token count for multi-page PDFs
            for b64_img in base64_pages[:3]:
                prompt_content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64_img}"},
                    }
                )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt_content},
            ]
        elif content_type == "text":
            content_snippet = self._create_representative_snippet(
                file_details.get("content", "")
            )
            if not content_snippet:
                return None
            # Append the snippet to the main user prompt for text files
            full_user_prompt = (
                f'{user_prompt_text}\n\nFILE CONTENT SNIPPET:\n"{content_snippet}"'
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_user_prompt},
            ]
        else:
            return None
        # print(f"Classifying file: {filename} with content type '{content_type}'")
        tool_name = "classify_file"
        # Assume FILE_CLASSIFICATION_SCHEMA is defined elsewhere
        tools = [
            {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": "Classifies a file against a checklist.",
                    "parameters": FILE_CLASSIFICATION_SCHEMA,
                },
            }
        ]

        try:
            response = self.client.chat.completions.create(
                model=model_to_use,
                messages=messages,
                tool_choice={"type": "function", "function": {"name": tool_name}},
                tools=tools,
                # max_completion_tokens=1000
            )
            tool_calls = response.choices[0].message.tool_calls
            if tool_calls:
                function_args = json.loads(tool_calls[0].function.arguments)
                # Assume FileClassification is a Pydantic model
                classification_data = FileClassification(**function_args)
                return classification_data
        except Exception as e:
            print(f"ERROR: AI classification failed for file '{filename}': {e}")
        # finally:
        # print("finished with classification. Returning result.")
        return None

    def validate_and_verify_document(
        self, file_details: Dict, document_definition: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validates a single file against a detailed document definition.

        This version is updated to accept a full document dictionary, which includes
        the specific 'checks' to perform, making the validation highly targeted.
        """
        issues = []
        if "content_type" not in file_details:
            issues.append("File is corrupted or in an unsupported format.")
            return {"is_valid": False, "issues": issues}

        # The prompt is now created using the full document definition.
        user_prompt_text = self._create_validation_prompt(
            file_details, document_definition
        )

        tool_name = "validate_document_quality"
        # Assume DOC_VALIDATION_SCHEMA is defined elsewhere
        tools = [
            {
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": "Reports the quality and authenticity findings for a document.",
                    "parameters": DOC_VALIDATION_SCHEMA,
                },
            }
        ]
        # print(f"Validating document: {file_details.get('filename', 'Unknown')} against checks: {document_definition.get('checks', [])}")
        try:
            model_to_use = "o3"
            validation_messages = []
            system_prompt = "You are a meticulous quality control inspector for legal and official documents. Your job is to find any potential issues based on a specific list of checks that would cause a document to be rejected."

            if file_details.get("content_type") in ["image", "pdf_images"]:
                image_data = file_details.get("image_data")
                if file_details.get("content_type") == "pdf_images":
                    # For multi-page PDFs, validate the first page for a quick check
                    base64_images = self._pdf_to_base64_images(image_data, dpi=150)
                    base64_image = base64_images[0] if base64_images else None
                else:
                    base64_image = base64.b64encode(image_data).decode("utf-8")

                if base64_image:
                    validation_messages = [
                        {"role": "system", "content": system_prompt},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": user_prompt_text},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    },
                                },
                            ],
                        },
                    ]
                else:
                    issues.append("Could not extract image from file for validation.")
            else:  # Text content
                validation_messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt_text},
                ]

            if not validation_messages:
                return {"is_valid": len(issues) == 0, "issues": issues}
            # print(f"Sending validation request for file: {file_details.get('filename', 'Unknown')}")
            response = self.client.chat.completions.create(
                model=model_to_use,
                messages=validation_messages,
                tool_choice={"type": "function", "function": {"name": tool_name}},
                tools=tools,
                # No max_completion_tokens needed here unless you want to limit the validation response size
            )
            tool_calls = response.choices[0].message.tool_calls
            if tool_calls:
                function_args = json.loads(tool_calls[0].function.arguments)
                # Assume DocumentValidation is a Pydantic model
                validation_data = DocumentValidation(**function_args)
                if not validation_data.is_valid:
                    issues.extend(validation_data.issues_found)
        except Exception as e:
            print(
                f"ERROR: AI validation failed for file '{file_details.get('filename')}': {e}"
            )
            issues.append("Automated quality check could not be completed.")
        # finally:
        #     print("Finished validation. Returning result.")

        return {"is_valid": len(issues) == 0, "issues": issues}

    def _create_validation_prompt(
        self, file_details: Dict, document_definition: Dict[str, Any]
    ) -> str:
        """
        Creates a detailed validation prompt for the AI, including specific checks.
        """
        filename = file_details.get("filename")
        doc_name = document_definition.get("document_name")
        doc_description = document_definition.get("description")
        specific_checks = "\n".join(
            [
                f"{i+1}. {check}"
                for i, check in enumerate(document_definition.get("checks", []))
            ]
        )

        prompt_text = (
            f"I have a file, '{filename}', that has been identified as a \"{doc_name}\".\n"
            f'The official description for this document is: "{doc_description}".\n\n'
            f"Please perform a thorough quality and authenticity check. Specifically, you MUST verify the following points:\n"
            f"--- SPECIFIC CHECKS ---\n{specific_checks}\n----------------------\n\n"
            f"In addition to the specific checks, also look for general issues like:\n"
            f"- **Clarity & Quality**: Is the content legible? Are there signs of blurriness, poor scanning, or glare?\n"
            f"- **Completeness**: Does the document appear complete? Are any parts cut off?\n"
            f"- **Authenticity**: Are there any obvious signs of digital alteration?\n\n"
            f"Use the `validate_document_quality` tool to report your findings. If the document fails any of the specific or general checks, list the reasons clearly."
        )

        if file_details.get("content_type") == "text":
            prompt_text += f"\n\nFull Text Content:\n\"{file_details.get('content')}\""

        return prompt_text

    def check_specific_file(
        self,
        checklist_item: list[str],
        file_details: Dict[str, Union[str, bytes]],
        is_test: bool = False,
    ) -> Dict[str, Any]:
        # if is_test:
        #     return {"document_name": checklist_item[0]["document_name"], "status": "Present", "file_url": file_details["file_url"], "reason": None}

        classification = self._classify_file_with_ai(file_details, checklist_item)
        print(
            f"Checking specific file: {file_details.get('filename', 'Unknown')} against checklist item: {checklist_item[0]['document_name']}"
        )
        if (
            not classification
            or classification.best_match != checklist_item[0]["document_name"]
        ):
            return {
                "document_name": checklist_item[0]["document_name"],
                "status": "Replace",
                "file_url": file_details["file_url"],
                "reason": "File does not appear to be the correct document type.",
            }

        validation_result = self.validate_and_verify_document(
            file_details, checklist_item[0]
        )

        final_status = "Present" if validation_result["is_valid"] else "Replace"
        return {
            "document_name": checklist_item[0]["document_name"],
            "status": final_status,
            "file_url": file_details["file_url"],
            "reason": (
                validation_result["issues"]
                if not validation_result["is_valid"]
                else None
            ),
        }


class DocumentCompiler:
    def __init__(self):
        self.temp_dir = "./tmp"
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)


    def _convert_image_to_pdf(self, image_bytes: bytes, output_path: str):
        """Converts image bytes into a single-page PDF."""
        try:
            image = Image.open(io.BytesIO(image_bytes))
            if image.mode == "P" or image.mode == "PA":
                image = (
                    image.convert("RGBA") if "A" in image.mode else image.convert("RGB")
                )

            c = canvas.Canvas(output_path, pagesize=letter)
            img_width, img_height = image.size
            page_width, page_height = letter
            aspect = img_height / float(img_width)

            new_width = page_width
            new_height = new_width * aspect
            if new_height > page_height:
                new_height = page_height
                new_width = new_height / aspect

            x_centered = (page_width - new_width) / 2
            y_centered = (page_height - new_height) / 2

            c.drawImage(
                ImageReader(image),
                x_centered,
                y_centered,
                width=new_width,
                height=new_height,
            )
            c.showPage()
            c.save()
        except Exception as e:
            print(f"Error converting image to PDF: {e}")

    def _convert_text_to_pdf(self, text_content: str, output_path: str):
        try:
            c = canvas.Canvas(output_path, pagesize=letter)
            width, height = letter
            text = c.beginText(72, height - 72)
            text.setFont("Helvetica", 10)

            for line in text_content.split("\n"):
                text.textLine(line)
                if text.getY() < 72:
                    c.drawText(text)
                    c.showPage()
                    text = c.beginText(72, height - 72)
                    text.setFont("Helvetica", 10)

            c.drawText(text)
            c.showPage()
            c.save()
        except Exception as e:
            print(f"Error converting text to PDF: {e}")

    def _convert_docx_to_pdf(self, docx_bytes: bytes, output_path: str):
        try:
            doc = Document(io.BytesIO(docx_bytes))
            full_text = "\n".join([para.text for para in doc.paragraphs])
            self._convert_text_to_pdf(full_text, output_path)
        except Exception as e:
            print(f"Error converting DOCX to PDF: {e}")

    def _merge_pdfs(self, pdf_paths: List[str], output_path: str):
        pdf_writer = PyPDF2.PdfWriter()
        print(len(pdf_paths))
        for path in pdf_paths:
            try:
                pdf_reader = PyPDF2.PdfReader(path)
                for page in pdf_reader.pages:
                    pdf_writer.add_page(page)
            except Exception as e:
                print(f"Could not read or add {path} to merger: {e}")

        # Ensure parent directory exists if it doesn't already
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Create and write the file
        with open(output_path, "wb") as out:
            pdf_writer.write(out)
        print(f"Successfully created compiled PDF at: {output_path}")

    def _cleanup(self):
        for f in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, f))
        # os.rmdir(self.temp_dir)
        # print("Temporary files cleaned up.")

    def compile_from_s3_urls(self, s3_urls: List[str], output_path: str) -> bool:
        temp_pdf_paths = []
        print(s3_urls)
        try:
            for i, url in enumerate(s3_urls):
                # print(f"Processing file {i+1}/{len(s3_urls)}: {url}")
                file_bytes = docs.download_file(url)
                if not file_bytes:
                    continue

                filename = os.path.basename(urlparse(url).path)
                ext = os.path.splitext(filename)[1].lower()
                temp_output_path = os.path.join(self.temp_dir, f"temp_{i}.pdf")

                if ext in [".jpg", ".jpeg", ".png", ".heic", ".bmp", ".tiff"]:
                    self._convert_image_to_pdf(file_bytes, temp_output_path)
                    temp_pdf_paths.append(temp_output_path)
                elif ext == ".txt":
                    self._convert_text_to_pdf(
                        file_bytes.decode("utf-8", errors="ignore"), temp_output_path
                    )
                    temp_pdf_paths.append(temp_output_path)
                elif ext == ".docx":
                    self._convert_docx_to_pdf(file_bytes, temp_output_path)
                    temp_pdf_paths.append(temp_output_path)
                elif ext == ".pdf":
                    # If it's already a PDF, save it to temp directory and standardize to letter size
                    try:
                        # Read the original PDF
                        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
                        pdf_writer = PyPDF2.PdfWriter()

                        # Process each page to letter size
                        for page in pdf_reader.pages:
                            page.scale_to(letter[0], letter[1])
                            pdf_writer.add_page(page)

                        # Save the standardized PDF
                        with open(temp_output_path, "wb") as f:
                            pdf_writer.write(f)
                        temp_pdf_paths.append(temp_output_path)
                    except Exception as e:
                        # print(f"Error standardizing PDF size: {e}")
                        # Fallback to original PDF if conversion fails
                        with open(temp_output_path, "wb") as f:
                            f.write(file_bytes)
                        temp_pdf_paths.append(temp_output_path)
                # else:
                #     print(f"Skipping unsupported file type: {filename}")

            if not temp_pdf_paths:
                return False

            # print("All files converted. Merging into final document...")
            self._merge_pdfs(temp_pdf_paths, output_path)
            return True

        except Exception as e:
            # print(f"A critical error occurred during compilation: {e}")
            return False
        # finally:
        #     # Exclude the output_path from deletion
        #     self._cleanup(exclude_files=[output_path])
