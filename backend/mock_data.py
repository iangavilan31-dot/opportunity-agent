"""
Realistic seed leads — used when RAPIDAPI_KEY is not configured so the full
pipeline (score -> research -> email) runs end-to-end with zero setup.

Each entry mirrors a real job posting: the responsibilities listed ARE the
repetitive workflows we sell automation against. Descriptions are intentionally
varied in tone/format to feel scraped, not generated.
"""
import hashlib
from datetime import datetime, timezone, timedelta
import random


def _job_id(company: str, title: str) -> str:
    return hashlib.md5(f"mock::{company}::{title}".encode()).hexdigest()


_SEED = [
    {
        "company_name": "Brightpath Staffing",
        "company_domain": "brightpathstaffing.com",
        "job_title": "Recruiting Coordinator",
        "job_location": "Austin, TX",
        "company_size": "small (10-50)",
        "job_description": """Brightpath Staffing is a fast-growing recruiting agency placing candidates in healthcare and logistics roles. We're hiring a Recruiting Coordinator to support our team of 6 recruiters.

Responsibilities:
- Schedule phone screens and interviews between candidates and hiring managers across multiple time zones
- Send interview confirmation and reminder emails to candidates
- Keep our ATS (Bullhorn) updated with candidate status changes throughout the pipeline
- Send follow-up emails to candidates who have gone quiet
- Generate weekly placement and pipeline reports for leadership
- Coordinate background checks and reference calls
- Post job openings to multiple job boards and track applicant flow

You'll spend a lot of time in email, our ATS, and spreadsheets. Strong organization and follow-through required. This is a high-volume role.""",
    },
    {
        "company_name": "Cedar Ridge Dental Group",
        "company_domain": "cedarridgedental.com",
        "job_title": "Patient Care Coordinator",
        "job_location": "Denver, CO",
        "company_size": "small (10-50)",
        "job_description": """Cedar Ridge Dental Group operates 4 dental practices in the Denver metro. We are seeking a Patient Care Coordinator to manage the patient experience from first call to follow-up.

Duties include:
- Answering patient calls and scheduling appointments across our locations
- Sending appointment reminders via phone, text, and email
- Following up with patients who missed or cancelled appointments to rebook
- Verifying insurance eligibility before appointments
- Entering and updating patient records in our practice management software (Dentrix)
- Processing intake forms for new patients
- Sending post-visit care instructions and review requests
- Managing the recall list and reaching out to patients due for cleanings

We see a high volume of patients daily. Reliability and attention to detail are essential.""",
    },
    {
        "company_name": "Summit Property Management",
        "company_domain": "summitpm.com",
        "job_title": "Operations Assistant",
        "job_location": "Phoenix, AZ",
        "company_size": "small (10-50)",
        "job_description": """Summit Property Management manages 1,200+ residential units across the Phoenix area. We need an Operations Assistant to keep our day-to-day running smoothly.

What you'll do:
- Coordinate maintenance requests between tenants and vendors
- Schedule property showings and inspections
- Send rent reminders and follow up on late payments
- Update unit availability across listing sites (Zillow, Apartments.com)
- Maintain tenant records and lease documents in our system (AppFolio)
- Generate monthly owner reports
- Process applications and run tenant screening
- Respond to routine tenant inquiries via email

Lots of repetitive coordination and data entry. We're growing fast and the admin load has outpaced our current team.""",
    },
    {
        "company_name": "Harborline Legal",
        "company_domain": "harborlinelegal.com",
        "job_title": "Legal Intake Coordinator",
        "job_location": "Tampa, FL",
        "company_size": "small (10-50)",
        "job_description": """Harborline Legal is a personal injury law firm. We are hiring a Legal Intake Coordinator to be the first point of contact for potential clients.

Key responsibilities:
- Answer incoming calls and web inquiries from potential clients
- Conduct initial intake interviews using our standard questionnaire
- Enter client information into our case management system (Clio)
- Schedule consultations with attorneys
- Send intake paperwork and follow up to ensure it's completed and returned
- Follow up with leads who haven't responded
- Generate daily intake reports
- Send status update emails to clients at key case milestones

This role involves a high volume of calls, repetitive data entry, and consistent follow-up. We lose leads when follow-up slips, so consistency matters.""",
    },
    {
        "company_name": "Pulse Digital Agency",
        "company_domain": "pulsedigital.co",
        "job_title": "Account Coordinator",
        "job_location": "Remote",
        "company_size": "small (10-50)",
        "job_description": """Pulse Digital is a marketing agency serving 30+ B2B clients. We're looking for an Account Coordinator to support our account managers.

Responsibilities:
- Schedule and coordinate client meetings and send calendar invites
- Compile weekly and monthly performance reports from Google Analytics, Meta Ads, and HubSpot
- Send recurring status update emails to clients
- Track project deliverables and deadlines in Asana
- Follow up with clients for assets, approvals, and feedback
- Onboard new clients (send welcome packets, collect intake info, set up accounts)
- Update CRM records after every client touchpoint
- Coordinate between design, content, and ads teams

A lot of this role is reporting, follow-up, and keeping our systems in sync. We want someone organized who can keep the trains running.""",
    },
    {
        "company_name": "Apex Logistics Solutions",
        "company_domain": "apexlogisticssolutions.com",
        "job_title": "Dispatch Coordinator",
        "job_location": "Columbus, OH",
        "company_size": "mid (50-200)",
        "job_description": """Apex Logistics is a regional freight brokerage. We are hiring a Dispatch Coordinator to manage carrier communications and load tracking.

Daily tasks:
- Assign loads to carriers and send dispatch confirmations
- Track shipments and provide status updates to customers
- Enter load and carrier details into our TMS
- Send check-in reminders to drivers
- Update delivery status and resolve routine exceptions
- Generate daily load board reports
- Follow up on missing paperwork (BOLs, PODs)
- Coordinate between customers, carriers, and warehouse teams

This is a fast-paced role with constant communication and data entry across phone, email, and our TMS.""",
    },
    {
        "company_name": "Comfort Air HVAC",
        "company_domain": "comfortairhvac.com",
        "job_title": "Service Scheduling Coordinator",
        "job_location": "Charlotte, NC",
        "company_size": "small (10-50)",
        "job_description": """Comfort Air is a residential HVAC company with 12 technicians. We need a Scheduling Coordinator to dispatch our service calls.

You will:
- Schedule service appointments and route technicians efficiently
- Call and text customers to confirm appointment windows
- Reschedule and follow up on cancelled appointments
- Enter job details and customer info into ServiceTitan
- Send invoices and follow up on unpaid balances
- Book seasonal maintenance for service-plan customers
- Generate technician productivity reports
- Handle inbound calls and book new service requests

Most of the day is spent scheduling, confirming, and following up. We need someone who can keep our techs busy and customers informed.""",
    },
    {
        "company_name": "Meridian Medical Billing",
        "company_domain": "meridianmedbilling.com",
        "job_title": "Data Entry Specialist",
        "job_location": "Remote",
        "company_size": "mid (50-200)",
        "job_description": """Meridian provides medical billing services to independent practices. We are hiring Data Entry Specialists to process claims and patient data.

Responsibilities:
- Enter patient demographics and insurance information into billing software
- Post charges and payments from EOBs
- Transfer data between practice systems and our billing platform
- Verify claim details before submission
- Flag and route claim denials for follow-up
- Generate weekly billing reports for client practices
- Reconcile payment records
- Update patient records with corrected information

This role is highly repetitive and detail-oriented — lots of moving data between systems accurately and quickly.""",
    },
    {
        "company_name": "Evergreen Wellness Studios",
        "company_domain": "evergreenwellness.com",
        "job_title": "Front Desk & Booking Coordinator",
        "job_location": "Portland, OR",
        "company_size": "micro (1-10)",
        "job_description": """Evergreen is a boutique wellness studio offering massage, acupuncture, and physical therapy. We're hiring a Booking Coordinator to manage our schedule and client communications.

What you'll handle:
- Book and confirm appointments across our practitioners
- Send appointment reminders and follow up on no-shows
- Manage the waitlist and fill last-minute cancellations
- Process intake forms for new clients
- Send rebooking reminders to clients who haven't returned
- Update client records and package/membership balances
- Respond to booking inquiries via email, phone, and Instagram DMs
- Send post-session follow-ups and review requests

We're small but busy. A lot of our day is scheduling, reminders, and follow-up that eats into time we'd rather spend with clients.""",
    },
    {
        "company_name": "Ironclad Insurance Group",
        "company_domain": "ironcladinsgroup.com",
        "job_title": "Policy Administration Assistant",
        "job_location": "Hartford, CT",
        "company_size": "mid (50-200)",
        "job_description": """Ironclad is an independent insurance agency. We are seeking a Policy Administration Assistant to support our producers.

Duties:
- Process policy applications and renewals
- Enter client and policy data into our agency management system (Applied Epic)
- Send renewal reminders and follow up on missing documents
- Generate certificates of insurance on request
- Follow up with carriers on pending submissions
- Prepare quote comparison spreadsheets
- Send policy documents to clients and confirm receipt
- Maintain accurate records across systems

Much of the role is repetitive document processing, data entry, and follow-up with clients and carriers.""",
    },
    {
        "company_name": "TruNorth Accounting",
        "company_domain": "trunorthaccounting.com",
        "job_title": "Client Services Coordinator",
        "job_location": "Minneapolis, MN",
        "company_size": "small (10-50)",
        "job_description": """TruNorth is a CPA firm serving small business clients. We need a Client Services Coordinator, especially heading into tax season.

Responsibilities:
- Schedule client meetings and send calendar invites
- Send document request checklists and follow up on missing items
- Track the status of returns and engagements in our workflow software
- Send reminders for quarterly estimates and deadlines
- Onboard new clients (engagement letters, intake forms, portal setup)
- Generate status reports for partners
- Respond to routine client questions via email
- Keep client records and contact info current

A huge part of this role is chasing documents, sending reminders, and keeping everyone on schedule. It's repetitive but critical.""",
    },
    {
        "company_name": "Blue Wave Pool Service",
        "company_domain": "bluewavepools.com",
        "job_title": "Operations Coordinator",
        "job_location": "San Diego, CA",
        "company_size": "small (10-50)",
        "job_description": """Blue Wave services 800+ residential and commercial pools. We're hiring an Operations Coordinator to manage routes and customer communication.

You'll be responsible for:
- Scheduling routes for our service technicians
- Sending service confirmations and reminders to customers
- Following up on missed payments and sending invoices
- Entering service records and customer notes into our system
- Handling inbound service requests and booking new customers
- Generating route and revenue reports
- Coordinating equipment repairs between customers and techs
- Managing seasonal opening/closing schedules

Most of the work is scheduling, reminders, billing follow-up, and data entry. We're growing and need help staying organized.""",
    },
    {
        "company_name": "Catalyst Recruiting Partners",
        "company_domain": "catalystrecruiting.com",
        "job_title": "Talent Coordinator",
        "job_location": "Chicago, IL",
        "company_size": "small (10-50)",
        "job_description": """Catalyst places software and product talent at startups. We need a Talent Coordinator to keep our search process moving.

Responsibilities:
- Schedule interviews across candidates and multiple client teams
- Send interview prep materials and confirmations to candidates
- Update candidate status in our ATS (Greenhouse) after each stage
- Send follow-up and nudge emails to candidates and clients
- Collect and route interview feedback
- Generate weekly pipeline reports for clients
- Coordinate offer and onboarding logistics
- Keep our database of candidates current and tagged

The role is scheduling-heavy with constant follow-up and CRM hygiene. Things slip through the cracks when we're busy — we need someone (or something) to catch them.""",
    },
    {
        "company_name": "Greenfield Home Care",
        "company_domain": "greenfieldhomecare.com",
        "job_title": "Care Scheduling Coordinator",
        "job_location": "Columbus, OH",
        "company_size": "mid (50-200)",
        "job_description": """Greenfield provides in-home care for seniors. We are hiring a Scheduling Coordinator to match caregivers with clients.

Daily work:
- Schedule caregiver shifts and match them to client needs
- Fill open and call-out shifts quickly
- Send shift confirmations and reminders to caregivers
- Update scheduling software with availability and changes
- Follow up on timesheets and missing clock-ins
- Coordinate between clients, families, and caregivers
- Generate scheduling and hours reports for billing
- Handle inbound scheduling requests and changes

This is a high-volume coordination role with constant scheduling changes, confirmations, and follow-up. Reliability is critical for client care.""",
    },
    {
        "company_name": "Vantage Real Estate Group",
        "company_domain": "vantagerealestategroup.com",
        "job_title": "Transaction Coordinator",
        "job_location": "Scottsdale, AZ",
        "company_size": "small (10-50)",
        "job_description": """Vantage is a residential real estate team closing 200+ deals a year. We need a Transaction Coordinator to manage deals from contract to close.

Responsibilities:
- Track transaction milestones and deadlines for every active deal
- Send reminders to agents, clients, lenders, and title companies
- Collect and organize transaction documents and signatures
- Update transaction status in our CRM
- Follow up on outstanding items to keep closings on track
- Send status updates to clients throughout the process
- Coordinate inspections, appraisals, and closing appointments
- Generate weekly pipeline and closing reports

This role lives in checklists, deadlines, and follow-up. A missed reminder can delay a closing, so consistency is everything.""",
    },
    {
        "company_name": "Stride Fitness Collective",
        "company_domain": "stridefitness.co",
        "job_title": "Membership Coordinator",
        "job_location": "Nashville, TN",
        "company_size": "small (10-50)",
        "job_description": """Stride operates 3 boutique fitness studios. We're hiring a Membership Coordinator to manage memberships and member communication.

You will:
- Process new memberships and handle cancellations/freezes
- Send class reminders and follow up with no-shows
- Reach out to members whose attendance has dropped (retention)
- Manage class scheduling and waitlists
- Update member records and billing in our system (Mindbody)
- Follow up on failed payments
- Send onboarding sequences to new members
- Respond to member inquiries across email and social

A lot of the role is repetitive member communication, retention follow-up, and billing administration.""",
    },
    {
        "company_name": "Northgate Auto Group",
        "company_domain": "northgateauto.com",
        "job_title": "Service BDC Representative",
        "job_location": "Kansas City, MO",
        "company_size": "mid (50-200)",
        "job_description": """Northgate Auto Group runs the business development center for our dealership service department. We are hiring a BDC Representative.

Responsibilities:
- Schedule service appointments from inbound calls and online requests
- Send appointment reminders and confirmations
- Follow up on declined service recommendations
- Call customers due for maintenance to book appointments
- Enter customer and vehicle data into our CRM and DMS
- Follow up after service visits for satisfaction and reviews
- Manage the recall and maintenance reminder campaigns
- Generate appointment and follow-up reports

High call volume with lots of scheduling, reminders, and structured follow-up. Much of the outreach follows the same scripts and cadences daily.""",
    },
    {
        "company_name": "Lumen Event Productions",
        "company_domain": "lumenevents.com",
        "job_title": "Event Coordination Assistant",
        "job_location": "Las Vegas, NV",
        "company_size": "small (10-50)",
        "job_description": """Lumen produces corporate events and conferences. We need an Event Coordination Assistant to support our planners.

Duties:
- Coordinate schedules between clients, vendors, and venues
- Send and track contracts, invoices, and payment reminders
- Maintain detailed event timelines and checklists
- Follow up with vendors for deliverables and confirmations
- Enter event details and contacts into our project system
- Send recurring status updates to clients
- Compile post-event reports and feedback surveys
- Manage RSVP lists and attendee communications

The role is coordination-heavy: lots of follow-up, document tracking, and keeping many parties aligned and on schedule.""",
    },
    {
        "company_name": "Keystone Mortgage Partners",
        "company_domain": "keystonemortgage.com",
        "job_title": "Loan Processing Assistant",
        "job_location": "Columbus, OH",
        "company_size": "mid (50-200)",
        "job_description": """Keystone is a mortgage brokerage. We're hiring a Loan Processing Assistant to support our loan officers through the pipeline.

Responsibilities:
- Collect and organize borrower documents
- Send document request lists and follow up on missing items
- Enter and verify loan data in our LOS (Encompass)
- Order appraisals, title, and verifications
- Send status updates to borrowers and agents
- Track conditions and deadlines for each file
- Follow up with borrowers who've gone quiet
- Generate pipeline status reports for management

This role is document- and follow-up-intensive. Files stall when we don't chase conditions, so consistent follow-up is essential.""",
    },
    {
        "company_name": "Bright Minds Tutoring",
        "company_domain": "brightmindstutoring.com",
        "job_title": "Scheduling & Family Coordinator",
        "job_location": "Remote",
        "company_size": "micro (1-10)",
        "job_description": """Bright Minds connects students with tutors for K-12 and test prep. We need a Coordinator to manage scheduling and family communication.

What you'll do:
- Match students with tutors and schedule recurring sessions
- Send session reminders to families and tutors
- Reschedule sessions and fill cancellations
- Follow up with families about progress and rebooking
- Process new family intake and tutor onboarding
- Track session hours and generate invoices
- Send progress reports compiled from tutor notes
- Respond to family inquiries via email and text

A lot of repetitive scheduling, reminders, billing, and family follow-up. We're a small team and the admin is eating our evenings.""",
    },
]


# A few extra archetypes to push past 20 and add variety in scoring
_EXTRA = [
    ("Coastal Veterinary Clinic", "coastalvetclinic.com", "Veterinary Receptionist & Scheduler", "Jacksonville, FL", "small (10-50)",
     "Busy small-animal vet clinic seeking a receptionist to book appointments, send vaccine and checkup reminders, follow up on missed appointments, enter patient records into our practice software, process intake for new pets, send post-visit instructions, and handle a high volume of phone and email scheduling. Repetitive reminders and record-keeping make up most of the day."),
    ("Pinnacle B2B Sales", "pinnacleb2b.com", "Sales Development Coordinator", "Boston, MA", "small (10-50)",
     "We support our outbound sales team. You'll schedule discovery calls, send meeting confirmations and reminders, update Salesforce after every touch, send follow-up sequences to prospects, route inbound leads, compile weekly pipeline reports, and keep CRM data clean. The role is CRM hygiene and follow-up heavy."),
    ("Maple Street Bakery Wholesale", "maplestreetwholesale.com", "Wholesale Order Coordinator", "Seattle, WA", "small (10-50)",
     "Growing wholesale bakery needs an Order Coordinator to take recurring orders from cafes and grocers, send order confirmations, enter orders into our system, coordinate delivery schedules with drivers, follow up on invoices, send standing-order reminders, and reconcile delivery records. Lots of repetitive order entry and standing-order management."),
    ("Horizon IT Services", "horizonitservices.com", "Service Desk Coordinator", "Dallas, TX", "mid (50-200)",
     "MSP seeking a Service Desk Coordinator to triage incoming tickets, schedule technician visits, send status updates to clients, follow up on open tickets, enter ticket details into our PSA (ConnectWise), generate SLA and ticket reports, and coordinate between clients and engineers. The role is ticket routing, scheduling, and structured follow-up."),
    ("Willowbrook Senior Living", "willowbrookseniorliving.com", "Admissions Coordinator", "Cincinnati, OH", "mid (50-200)",
     "Senior living community hiring an Admissions Coordinator to manage inquiries from families, schedule tours, send follow-up emails to prospects, process admission paperwork, enter resident data into our system, coordinate move-in logistics, and generate occupancy and inquiry reports. Lots of follow-up with families and repetitive paperwork."),
    ("Forge Manufacturing Supply", "forgemfgsupply.com", "Inside Sales Support Specialist", "Cleveland, OH", "mid (50-200)",
     "Industrial supply distributor seeking support for our inside sales team. Responsibilities include processing purchase orders, sending order confirmations and shipping updates, entering orders into our ERP, following up on quotes, generating recurring customer reports, and maintaining account records. Repetitive order processing and quote follow-up dominate the role."),
    ("Sunrise Pediatric Therapy", "sunrisepediatrictherapy.com", "Intake & Authorization Coordinator", "Orlando, FL", "small (10-50)",
     "Pediatric therapy clinic (OT/PT/Speech) needs a Coordinator to handle new patient intake, verify insurance and obtain authorizations, schedule evaluations and recurring therapy sessions, send appointment reminders, follow up on missing paperwork, enter data into our EMR, and track authorization expirations. Heavy on verification, scheduling, and follow-up."),
    ("Anchor Web Studio", "anchorwebstudio.com", "Project Coordinator", "Remote", "micro (1-10)",
     "Web design studio needs a Project Coordinator to schedule client kickoffs and check-ins, send recurring project status updates, chase clients for content and approvals, track deliverables in our PM tool, send invoices and payment reminders, onboard new clients, and keep our CRM updated. Lots of client follow-up and status reporting."),
    ("Riverside Plumbing Co", "riversideplumbingco.com", "Dispatcher / Office Coordinator", "Sacramento, CA", "small (10-50)",
     "Plumbing company with 9 trucks needs a dispatcher to schedule and route service calls, confirm appointments by call and text, follow up on estimates, enter jobs into our field service software, send invoices and chase payments, book recurring maintenance, and generate daily reports. The day is scheduling, confirmations, and billing follow-up."),
    ("Elevate Bookkeeping", "elevatebookkeeping.com", "Client Onboarding Coordinator", "Remote", "micro (1-10)",
     "Bookkeeping firm for small businesses needs a Coordinator to onboard new clients, send document and access request checklists, follow up on missing items, schedule monthly review calls, send recurring reminders for receipts and statements, update client records, and generate status reports. Highly repetitive onboarding and document chasing."),
    ("Trailhead Outdoor Rentals", "trailheadrentals.com", "Reservations Coordinator", "Boulder, CO", "small (10-50)",
     "Outdoor gear and vehicle rental company needs a Reservations Coordinator to process bookings, send confirmation and pickup reminders, follow up on returns, enter reservations into our system, handle inbound booking inquiries, manage the waitlist for popular items, send post-rental review requests, and generate utilization reports. Repetitive booking and reminder workflows."),
    ("Cornerstone Roofing", "cornerstoneroofingpros.com", "Sales & Production Coordinator", "Atlanta, GA", "small (10-50)",
     "Roofing contractor needs a Coordinator to schedule inspections and installations, send appointment confirmations, follow up on outstanding estimates, coordinate between sales reps and crews, enter jobs and customer info into our CRM, send insurance documentation, follow up on financing paperwork, and generate production reports. Scheduling and follow-up intensive."),
    ("Verde Landscaping Group", "verdelandscaping.com", "Account & Scheduling Coordinator", "Austin, TX", "small (10-50)",
     "Commercial landscaping company needs a Coordinator to schedule recurring maintenance crews, send service confirmations to property managers, follow up on proposals, enter work orders into our system, handle billing and payment follow-up, coordinate seasonal services, and generate route and revenue reports. Repetitive scheduling and billing administration."),
    ("Beacon Behavioral Health", "beaconbehavioralhealth.com", "Patient Scheduling Specialist", "Remote", "mid (50-200)",
     "Behavioral health practice needs a Scheduling Specialist to book and confirm therapy appointments, manage waitlists, send appointment reminders, follow up on no-shows and cancellations, verify insurance, enter patient data into our EHR, send intake paperwork, and generate scheduling reports. High-volume scheduling and reminder workflows."),
    ("Quantum Financial Advisors", "quantumfinadvisors.com", "Client Service Associate", "Charlotte, NC", "small (10-50)",
     "Financial advisory firm needs a Client Service Associate to schedule client review meetings, send meeting prep and reminders, process account paperwork, follow up on outstanding documents, update CRM records, send recurring portfolio summaries, onboard new clients, and generate client reports. Document processing and recurring client communication heavy."),
    ("Skyline Window Cleaning", "skylinewindowcleaning.com", "Office & Scheduling Coordinator", "Denver, CO", "micro (1-10)",
     "Window cleaning company needs a Coordinator to schedule jobs, confirm appointments by text and email, follow up on quotes, enter jobs into our scheduling software, send invoices and chase payments, book recurring service customers, and respond to booking inquiries. The role is mostly scheduling, confirmations, and billing follow-up."),
    ("Heritage Title Company", "heritagetitleco.com", "Title Processing Coordinator", "Houston, TX", "mid (50-200)",
     "Title company needs a Processing Coordinator to open title orders, request payoffs and documents, send status updates to agents and lenders, track file deadlines, follow up on outstanding items, enter data into our title software, coordinate closings, and generate pipeline reports. Document- and deadline-driven with constant follow-up."),
    ("Nimbus SaaS", "nimbussaas.io", "Customer Onboarding Coordinator", "Remote", "small (10-50)",
     "B2B SaaS company needs an Onboarding Coordinator to schedule kickoff and training calls, send onboarding sequences and reminders, track onboarding milestones, follow up on incomplete setups, update CRM and onboarding tracker, send check-in emails, escalate stalled accounts, and generate onboarding reports. Repetitive scheduling and structured follow-up."),
    ("Oakwood Construction", "oakwoodconstruction.com", "Project Administrative Coordinator", "Portland, OR", "mid (50-200)",
     "General contractor needs a Coordinator to track project documents and submittals, send reminders to subcontractors, schedule inspections, follow up on outstanding paperwork and lien waivers, enter data into our project management system, generate progress reports, and coordinate between PMs, subs, and owners. Document tracking and follow-up intensive."),
    ("Citrus Marketing Co", "citrusmarketing.co", "Client Reporting Coordinator", "Remote", "small (10-50)",
     "Performance marketing agency needs a Coordinator focused on reporting and client communication. You'll compile weekly and monthly reports from ad platforms and analytics, send recurring performance updates, schedule client review calls, follow up for assets and approvals, update the CRM, and onboard new clients. Heavy on recurring reporting and follow-up."),
]

for name, domain, title, loc, size, desc in _EXTRA:
    _SEED.append({
        "company_name": name,
        "company_domain": domain,
        "job_title": title,
        "job_location": loc,
        "company_size": size,
        "job_description": desc,
    })


def get_mock_jobs(limit: int = 50) -> list[dict]:
    """Return realistic seed jobs formatted exactly like scraper output."""
    jobs = []
    now = datetime.now(timezone.utc)
    pool = _SEED[:limit] if limit else _SEED
    for i, entry in enumerate(pool):
        posted = now - timedelta(days=random.randint(0, 6), hours=random.randint(0, 23))
        jobs.append({
            "job_id": _job_id(entry["company_name"], entry["job_title"]),
            "source": "mock",
            "job_url": f"https://{entry['company_domain']}/careers",
            "company_name": entry["company_name"],
            "company_domain": entry["company_domain"],
            "company_linkedin": "",
            "job_title": entry["job_title"],
            "job_description": entry["job_description"],
            "job_location": entry["job_location"],
            "job_posted_at": posted,
        })
    return jobs
