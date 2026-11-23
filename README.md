# Personal Blog CMS

A Django-based personal blog and content management system. It supports article creation and management, scheduled publishing, categories and tags, author profiles, comment moderation, email subscriptions, notifications, RSS and Atom feeds, sitemap generation, and visitor tracking.

## Features

- **Article management:** Create, edit, and delete articles.
- **Article statuses:** Save articles as drafts, publish them immediately, or schedule them for later publication.
- **Rich-text content:** Use CKEditor 5 for article content.
- **Author management:** Associate articles with author profiles and provide an author dashboard.
- **Categories and tags:** Organize articles and filter the public article list.
- **Comments:** Allow authenticated users to submit comments and provide a moderation workflow.
- **Subscriptions:** Allow users to subscribe to authors.
- **Notifications:** Create and process email notifications for newly published articles.
- **Feeds:** Provide RSS and Atom feeds.
- **Sitemap:** Generate an XML sitemap for published articles.
- **Visitor tracking:** Use custom middleware to track page views and unique visitors.
- **Authentication:** Support user registration, login, and logout.
- **Security:** Sanitize submitted rich-text content using `nh3`.

## Technology Stack

- Python
- Django 6.1.3
- SQLite
- django-ckeditor-5
- django-taggit
- nh3
- python-dotenv
- HTML and CSS

## Project Structure

```text
django-personal-blog-cms/
├── blog/
│   ├── management/
│   │   └── commands/
│   ├── static/
│   │   └── blog/
│   │       └── css/
│   ├── templates/
│   │   ├── blog/
│   │   └── registration/
│   ├── tests/
│   ├── admin.py
│   ├── feeds.py
│   ├── forms.py
│   ├── middleware.py
│   ├── models.py
│   ├── sanitizers.py
│   ├── services.py
│   ├── sitemaps.py
│   ├── urls.py
│   └── views.py
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── manage.py
├── requirements.txt
└── README.md
```

## Installation and Setup

The following instructions are for a local Windows development environment.

### 1. Clone the repository

```powershell
git clone <repository-url>
cd django-personal-blog-cms
```

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root, alongside `manage.py`.

Add the following variables:

```dotenv
SECRET_KEY=your-generated-secret-key
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
SITE_URL=http://127.0.0.1:8000
```

Generate a new Django secret key for your local environment. Keep the `.env` file private and do not commit it to version control.

The project uses `python-dotenv` to load environment variables from this file.

### 5. Apply database migrations

```powershell
python manage.py migrate
```

### 6. Create an administrator account

```powershell
python manage.py createsuperuser
```

### 7. Start the development server

```powershell
python manage.py runserver
```

Open `http://127.0.0.1:8000/` in your browser.

The Django administration panel is available at `http://127.0.0.1:8000/admin/`.

## Email Configuration

### Development email backend

The development environment uses Django's console email backend.

Emails are printed in the terminal where the development server or management command is running. They are not sent to real email addresses.

### Testing email locally

To test the email configuration, open the Django shell:

```powershell
python manage.py shell
```

Then execute:

```python
from django.core.mail import send_mail

send_mail(
    "Test email",
    "This is a development email test.",
    None,
    ["test@example.com"],
)
```

The email content should appear in the terminal. No real email is sent.

## Running Tests

Run the complete test suite with:

```powershell
python manage.py test
```

## Background Management Commands

The project includes two custom Django management commands.

### Publish scheduled articles

```powershell
python manage.py publish_scheduled_articles
```

Publishes articles whose scheduled publication time has arrived.

### Process pending email notifications

```powershell
python manage.py send_pending_notifications
```

Processes pending notification deliveries.

These commands must be invoked manually or configured with an external scheduler to run automatically.

## Application URLs

| URL | Purpose |
|---|---|
| `/` | Public article listing |
| `/accounts/` | Django authentication URLs |
| `/admin/` | Django administration |
| `/sitemap.xml` | XML sitemap |

The blog application's other routes are defined in `blog/urls.py`.

## Database

The project uses SQLite for local development. Running `python manage.py migrate` creates the database schema.

## Development Notes

- The project uses Django's built-in authentication system.
- Author-specific permissions control access to article management.
- Only published articles are intended to appear on the public blog.
- Scheduled publishing and notification processing are handled through custom management commands.
- The project is configured for local development and has not been presented as a production deployment.