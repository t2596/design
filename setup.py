"""车联网安全通信网关系统安装脚本"""

from setuptools import setup, find_packages

setup(
    name="vehicle-iot-security-gateway",
    version="0.1.0",
    description="基于国密算法的车联网安全通信网关系统",
    author="Vehicle IoT Security Team",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "gmssl>=3.2.2",
        "psycopg2-binary>=2.9.9",
        "redis>=5.0.1",
        "fastapi>=0.109.0",
        "uvicorn[standard]>=0.27.0",
        "pydantic>=2.5.3",
        "pytest>=7.4.4",
        "pytest-asyncio>=0.23.3",
        "hypothesis>=6.98.3",
        "python-dotenv>=1.0.0",
        "cryptography>=42.0.0",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
