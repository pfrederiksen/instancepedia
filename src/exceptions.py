"""Custom exceptions for Instancepedia"""


class InstancepediaError(Exception):
    """Base exception for all Instancepedia errors"""
    pass


class AWSError(InstancepediaError):
    """Base exception for AWS-related errors"""
    pass


class AWSCredentialsError(AWSError):
    """Raised when AWS credentials are missing or invalid"""
    pass


class AWSConnectionError(AWSError):
    """Raised when unable to connect to AWS"""
    pass


class AWSRateLimitError(AWSError):
    """Raised when AWS API rate limit is exceeded"""
    pass


class AWSRegionError(AWSError):
    """Raised when AWS region is invalid or not accessible"""
    pass


class PricingError(InstancepediaError):
    """Raised when pricing data cannot be fetched"""
    pass


class InstanceTypeError(InstancepediaError):
    """Raised when instance type data cannot be fetched"""
    pass


class ConfigurationError(InstancepediaError):
    """Raised when configuration is invalid"""
    pass
