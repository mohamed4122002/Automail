"""
Email provider abstraction layer.
Supports multiple providers: SendGrid, AWS SES, SMTP
Configuration loaded dynamically from Settings table.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class EmailProvider(ABC):
    """Abstract base class for email providers."""
    
    @abstractmethod
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Send an email.
        
        Returns:
            message_id: Provider-specific message ID for tracking
        """
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if the provider is configured correctly."""
        pass


class SendGridProvider(EmailProvider):
    """SendGrid email provider."""
    
    def __init__(self, api_key: str, from_email: str, from_name: str):
        self.api_key = api_key
        self.from_email = from_email
        self.from_name = from_name
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        unsubscribe_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Send email via SendGrid API."""
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, CustomArg
            
            message = Mail(
                from_email=(from_email or self.from_email, from_name or self.from_name),
                to_emails=to_email,
                subject=subject,
                html_content=html_body
            )
            
            # Add List-Unsubscribe header
            if unsubscribe_url:
                message.add_header("List-Unsubscribe", f"<{unsubscribe_url}>")
            
            # Add List-Unsubscribe header
            if unsubscribe_url:
                message.add_header("List-Unsubscribe", f"<{unsubscribe_url}>")
            
            # Add custom metadata for tracking
            if metadata:
                for key, value in metadata.items():
                    message.add_custom_arg(CustomArg(key, str(value)))
            
            sg = SendGridAPIClient(self.api_key)
            response = sg.send(message)
            
            # Extract message ID from headers
            message_id = response.headers.get('X-Message-Id', 'unknown')
            
            logger.info(f"SendGrid email sent to {to_email}, message_id: {message_id}")
            return message_id
            
        except Exception as e:
            logger.error(f"SendGrid send failed: {e}")
            raise
    
    async def test_connection(self) -> bool:
        """Test SendGrid API key validity."""
        try:
            from sendgrid import SendGridAPIClient
            sg = SendGridAPIClient(self.api_key)
            # Test with a simple API call
            response = sg.client.api_keys.get()
            return response.status_code == 200
        except Exception as e:
            logger.error(f"SendGrid connection test failed: {e}")
            return False


class AWSESProvider(EmailProvider):
    """AWS SES email provider."""
    
    def __init__(
        self, 
        aws_access_key: str, 
        aws_secret_key: str, 
        aws_region: str,
        from_email: str,
        from_name: str
    ):
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        self.aws_region = aws_region
        self.from_email = from_email
        self.from_name = from_name
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        unsubscribe_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Send email via AWS SES using send_raw_email to support custom headers."""
        try:
            import boto3
            from botocore.exceptions import ClientError
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            
            client = boto3.client(
                'ses',
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.aws_region
            )
            
            sender = f"{from_name or self.from_name} <{from_email or self.from_email}>"
            
            # Construct MIME message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = sender
            msg['To'] = to_email
            
            # Add List-Unsubscribe header
            if unsubscribe_url:
                msg['List-Unsubscribe'] = f"<{unsubscribe_url}>"
            
            # Add metadata as X-headers (optional but good for tracking in raw email)
            if metadata:
                for key, value in metadata.items():
                    msg[f'X-{key}'] = str(value)
            
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            # Prepare tags for SES tracking
            tags = [
                {'Name': key, 'Value': str(value)}
                for key, value in (metadata or {}).items()
            ]
            
            response = client.send_raw_email(
                Source=sender,
                Destinations=[to_email],
                RawMessage={'Data': msg.as_string()},
                Tags=tags
            )
            
            message_id = response['MessageId']
            logger.info(f"AWS SES raw email sent to {to_email}, message_id: {message_id}")
            return message_id
            
        except ClientError as e:
            logger.error(f"AWS SES send_raw_email failed: {e}")
            raise
    
    async def test_connection(self) -> bool:
        """Test AWS SES credentials."""
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            client = boto3.client(
                'ses',
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.aws_region
            )
            
            # Test with get_send_quota
            client.get_send_quota()
            return True
        except ClientError as e:
            logger.error(f"AWS SES connection test failed: {e}")
            return False


class SMTPProvider(EmailProvider):
    """SMTP email provider (fallback)."""
    
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        from_email: str,
        from_name: str,
        use_tls: bool = True
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.from_email = from_email
        self.from_name = from_name
        self.use_tls = use_tls
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        unsubscribe_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Send email via SMTP."""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            import uuid
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{from_name or self.from_name} <{from_email or self.from_email}>"
            msg['To'] = to_email
            
            # Add List-Unsubscribe header
            if unsubscribe_url:
                msg['List-Unsubscribe'] = f"<{unsubscribe_url}>"
            
            # Generate message ID
            message_id = str(uuid.uuid4())
            msg['Message-ID'] = f"<{message_id}@{self.smtp_host}>"
            
            # Add metadata as custom headers
            if metadata:
                for key, value in metadata.items():
                    msg[f'X-{key}'] = str(value)
            
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            # Connect and send
            logger.info(f"SMTP connecting to {self.smtp_host}:{self.smtp_port} for {to_email}")
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
                # server.set_debuglevel(1) # Enable for extremely verbose low-level network trace
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30)
            
            logger.info(f"SMTP authenticating as {self.smtp_username}")
            server.login(self.smtp_username, self.smtp_password)
            
            logger.info(f"SMTP sending message to {to_email}...")
            server.send_message(msg)
            server.quit()
            
            logger.info(f"SMTP email SENT successfully to {to_email}, message_id: {message_id}")
            return message_id
            
        except Exception as e:
            logger.error(f"SMTP send failed: {e}")
            raise
    
    async def test_connection(self) -> bool:
        """Test SMTP connection."""
        try:
            import smtplib
            
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=10)
            
            server.login(self.smtp_username, self.smtp_password)
            server.quit()
            return True
        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False


class ConsoleProvider(EmailProvider):
    """Console-only provider for development/testing."""
    
    def __init__(self, from_email: str = "test@example.com", from_name: str = "System Test"):
        self.from_email = from_email
        self.from_name = from_name
        
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        unsubscribe_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Log email to console instead of sending."""
        import uuid
        message_id = str(uuid.uuid4())
        
        logger.info(f"""
        [SIMULATION] REAL EMAIL NOT SENT (Console Mode)
        ==============================================
        To: {to_email}
        From: {from_name or self.from_name} <{from_email or self.from_email}>
        Subject: {subject}
        Message ID: {message_id}
        Unsubscribe-URL: {unsubscribe_url}
        Metadata: {metadata}
        ----------------------------------------------
        Body: {html_body[:500]}...
        ==============================================
        """)
        
        return message_id
    
    async def test_connection(self) -> bool:
        """Console provider is always available."""
        return True


async def get_email_provider() -> EmailProvider:
    """
    Get the configured email provider from Settings table (MongoDB/Beanie).
    """
    try:
        from .services.settings import SettingsService
        
        service = SettingsService()
        setting = await service.get_setting("email_provider")
        return await _create_provider_from_setting(setting)

    except Exception as e:
        logger.error(f"Failed to load email provider config: {e}")
        logger.warning("Falling back to Console provider")
        return ConsoleProvider()


async def _create_provider_from_setting(setting) -> EmailProvider:
    """Helper to create provider instance from setting object."""
    if not setting:
        logger.warning("No email provider configured in settings table, defaulting to Console.")
        return ConsoleProvider()
    
    config = setting.value
    provider_type = config.get("provider", "console")
    
    logger.info(f"Creating email provider of type: {provider_type}")
    
    if provider_type == "sendgrid":
        api_key = config.get("api_key")
        from_email = config.get("from_email")
        from_name = config.get("from_name")
        
        if not api_key or not from_email:
            logger.error(f"SendGrid config incomplete (key present: {bool(api_key)}, from present: {bool(from_email)})")
            return ConsoleProvider()
        
        return SendGridProvider(
            api_key=api_key,
            from_email=from_email,
            from_name=from_name or "Marketing Automation"
        )
            
    elif provider_type == "ses":
        aws_access_key = config.get("aws_access_key")
        aws_secret_key = config.get("aws_secret_key")
        aws_region = config.get("aws_region", "us-east-1")
        from_email = config.get("from_email")
        from_name = config.get("from_name")
        
        if not aws_access_key or not aws_secret_key or not from_email:
            logger.error(f"AWS SES config incomplete (access: {bool(aws_access_key)}, secret: {bool(aws_secret_key)}, from: {bool(from_email)})")
            return ConsoleProvider()
        
        return AWSESProvider(
            aws_access_key=aws_access_key,
            aws_secret_key=aws_secret_key,
            aws_region=aws_region,
            from_email=from_email,
            from_name=from_name or "Marketing Automation"
        )
    
    elif provider_type == "smtp":
        smtp_host = config.get("smtp_host")
        smtp_port = config.get("smtp_port", 587)
        smtp_username = config.get("smtp_username")
        smtp_password = config.get("smtp_password")
        from_email = config.get("from_email")
        from_name = config.get("from_name")
        use_tls = config.get("use_tls", True)
        
        if not smtp_host or not smtp_username or not smtp_password or not from_email:
            logger.error(f"SMTP config incomplete (host: {bool(smtp_host)}, user: {bool(smtp_username)}, pass: {bool(smtp_password)}, from: {bool(from_email)})")
            return ConsoleProvider()
        
        return SMTPProvider(
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_username=smtp_username,
            smtp_password=smtp_password,
            from_email=from_email,
            from_name=from_name or "Marketing Automation",
            use_tls=use_tls
        )
    
    elif provider_type == "console":
        logger.info("Explicitly using Console provider (Simulation Mode)")
        return ConsoleProvider()
    
    else:
        logger.warning(f"Unknown provider type: {provider_type} (config keys: {list(config.keys())}), using Console")
        return ConsoleProvider()


async def test_email_provider_config(config: dict) -> tuple[bool, str]:
    """
    Test email provider configuration without saving it.
    
    Args:
        config: Provider configuration dictionary
        
    Returns:
        (success: bool, message: str)
    """
    try:
        provider_type = config.get("provider", "console")
        
        if provider_type == "console":
            return True, "Console provider is always available"
        
        # Create provider instance based on config
        if provider_type == "sendgrid":
            provider = SendGridProvider(
                api_key=config.get("api_key"),
                from_email=config.get("from_email"),
                from_name=config.get("from_name", "Test")
            )
        elif provider_type == "ses":
            provider = AWSESProvider(
                aws_access_key=config.get("aws_access_key"),
                aws_secret_key=config.get("aws_secret_key"),
                aws_region=config.get("aws_region", "us-east-1"),
                from_email=config.get("from_email"),
                from_name=config.get("from_name", "Test")
            )
        elif provider_type == "smtp":
            provider = SMTPProvider(
                smtp_host=config.get("smtp_host"),
                smtp_port=config.get("smtp_port", 587),
                smtp_username=config.get("smtp_username"),
                smtp_password=config.get("smtp_password"),
                from_email=config.get("from_email"),
                from_name=config.get("from_name", "Test"),
                use_tls=config.get("use_tls", True)
            )
        else:
            return False, f"Unknown provider type: {provider_type}"
        
        # Test connection
        is_valid = await provider.test_connection()
        
        if is_valid:
            return True, f"{provider_type.upper()} connection successful"
        else:
            return False, f"{provider_type.upper()} connection failed"
            
    except Exception as e:
        return False, f"Test failed: {str(e)}"
