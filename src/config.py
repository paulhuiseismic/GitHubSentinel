import json
import os
from dotenv import load_dotenv

class Config:
    def __init__(self):
        self.load_config()
    
    def load_config(self):
        # Load environment variables from .env file
        load_dotenv()

        with open('config.json', 'r') as f:
            config = json.load(f)
            
            self.email = config.get('email', {})
            self.email['password'] = os.getenv('EMAIL_PASSWORD', self.email.get('password', ''))

            # 加载 GitHub 相关配置
            github_config = config.get('github', {})
            self.github_token = os.getenv('GITHUB_TOKEN', github_config.get('token'))
            self.subscriptions_file = github_config.get('subscriptions_file')
            self.freq_days = github_config.get('progress_frequency_days', 1)
            self.exec_time = github_config.get('progress_execution_time', "08:00")

            # 加载 LLM 相关配置
            llm_config = config.get('llm', {})
            self.llm_model_type = llm_config.get('model_type', 'openai')
            self.openai_model_name = llm_config.get('openai_model_name', 'gpt-4o-mini')
            self.ollama_model_name = llm_config.get('ollama_model_name', 'llama3')
            self.ollama_api_url = llm_config.get('ollama_api_url', 'http://localhost:11434/api/chat')

            # Azure / Azure Foundry settings (support both nested `azure` block or flat keys)
            azure_block = llm_config.get('azure', {}) if isinstance(llm_config.get('azure', {}), dict) else {}
            self.azure_base_url = llm_config.get('azure_base_url') or azure_block.get('base_url')
            self.azure_deployment_name = llm_config.get('azure_deployment_name') or azure_block.get('deployment_name')
            # allow API key to come from env var AZURE_OPENAI_KEY for security
            self.azure_api_key = os.getenv('AZURE_OPENAI_KEY', llm_config.get('azure_api_key') or azure_block.get('api_key'))
            self.azure_api_version = llm_config.get('azure_api_version') or azure_block.get('api_version') or '2023-05-15'

            # 加载报告类型配置
            self.report_types = config.get('report_types', ["github", "hacker_news"])  # 默认报告类型
            
            # 加载 Slack 配置
            slack_config = config.get('slack', {})
            self.slack_webhook_url = slack_config.get('webhook_url')
