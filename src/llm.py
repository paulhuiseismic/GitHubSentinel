import requests
from openai import OpenAI  # 导入OpenAI库用于访问GPT模型
from logger import LOG  # 导入日志模块

class LLM:
    def __init__(self, config):
        """
        初始化 LLM 类，根据配置选择使用的模型（OpenAI / Azure OpenAI / Ollama）。

        :param config: 配置对象，包含所有的模型配置参数。
        """
        self.config = config
        self.model = config.llm_model_type.lower()  # 获取模型类型并转换为小写
        if self.model == "openai":
            # 标准 OpenAI (OpenAI-hosted)
            self.client = OpenAI()
        elif self.model == "azure" or self.model == "azure_openai":
            # Azure OpenAI / Azure Foundry: validate required settings
            if not self.config.azure_base_url or not self.config.azure_deployment_name or not self.config.azure_api_key:
                LOG.error("Azure OpenAI 配置不完整: base_url, deployment_name 和 api_key 必须提供")
                raise ValueError("Azure OpenAI configuration incomplete: azure_base_url, azure_deployment_name, azure_api_key required")
            # keep base settings, we'll call REST endpoint directly using requests
            self.azure_base_url = self.config.azure_base_url.rstrip('/')
            self.azure_deployment_name = self.config.azure_deployment_name
            self.azure_api_key = self.config.azure_api_key
            self.azure_api_version = getattr(self.config, 'azure_api_version', '2023-05-15')
        elif self.model == "ollama":
            self.api_url = config.ollama_api_url  # 设置Ollama API的URL
        else:
            LOG.error(f"不支持的模型类型: {self.model}")
            raise ValueError(f"不支持的模型类型: {self.model}")  # 如果模型类型不支持，抛出错误

    def generate_report(self, system_prompt, user_content):
        """
        生成报告，根据配置选择不同的模型来处理请求。

        :param system_prompt: 系统提示信息，包含上下文和规则。
        :param user_content: 用户提供的内容，通常是Markdown格式的文本。
        :return: 生成的报告内容。
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]

        # 根据选择的模型调用相应的生成报告方法
        if self.model == "openai":
            return self._generate_report_openai(messages)
        elif self.model == "azure" or self.model == "azure_openai":
            return self._generate_report_azure(messages)
        elif self.model == "ollama":
            return self._generate_report_ollama(messages)
        else:
            raise ValueError(f"不支持的模型类型: {self.model}")

    def _generate_report_openai(self, messages):
        """
        使用 OpenAI GPT 模型生成报告（OpenAI 托管）。

        :param messages: 包含系统提示和用户内容的消息列表。
        :return: 生成的报告内容。
        """
        LOG.info(f"使用 OpenAI {self.config.openai_model_name} 模型生成报告。")
        try:
            response = self.client.chat.completions.create(
                model=self.config.openai_model_name,  # 使用配置中的OpenAI模型名称
                messages=messages
            )
            LOG.debug("GPT 响应: {}", response)
            return response.choices[0].message.content  # 返回生成的报告内容
        except Exception as e:
            LOG.error(f"生成报告时发生错误：{e}")
            raise

    def _generate_report_azure(self, messages):
        """
        使用 Azure OpenAI（包括 Azure Foundry 部署）通过 REST API 生成报告。

        :param messages: 包含系统提示和用户内容的消息列表。
        :return: 生成的报告内容。
        """
        LOG.info(f"使用 Azure OpenAI 部署 {self.azure_deployment_name} 生成报告。")
        try:
            # 构建 Azure OpenAI Chat Completions REST API 路径
            url = f"{self.azure_base_url}/openai/deployments/{self.azure_deployment_name}/chat/completions?api-version={self.azure_api_version}"

            payload = {
                "messages": messages,
                "max_tokens": 4000,
                "temperature": 0.7,
                "top_p": 1
            }

            headers = {
                "Content-Type": "application/json",
                # Azure OpenAI 使用 `api-key` 头部
                "api-key": self.azure_api_key
            }

            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            LOG.debug("Azure OpenAI 响应: {}", data)

            # 标准 Azure OpenAI 返回 choices -> [ { message: { role, content } } ]
            choices = data.get('choices') or []
            if not choices:
                LOG.error("Azure OpenAI 返回的响应中没有 choices: %s", data)
                raise ValueError("Azure OpenAI response missing choices")

            message = choices[0].get('message') or {}
            content = message.get('content')
            if content:
                return content

            LOG.error("无法从 Azure OpenAI 响应中提取文本: %s", data)
            raise ValueError("Cannot extract text from Azure OpenAI response")
        except Exception as e:
            LOG.error(f"生成报告时发生错误（Azure）: {e}")
            raise

    def _generate_report_ollama(self, messages):
        """
        使用 Ollama LLaMA 模型生成报告。

        :param messages: 包含系统提示和用户内容的消息列表。
        :return: 生成的报告内容。
        """
        LOG.info(f"使用 Ollama {self.config.ollama_model_name} 模型生成报告。")
        try:
            payload = {
                "model": self.config.ollama_model_name,  # 使用配置中的Ollama模型名称
                "messages": messages,
                "max_tokens": 4000,
                "temperature": 0.7,
                "stream": False
            }

            response = requests.post(self.api_url, json=payload)  # 发送POST请求到Ollama API
            response_data = response.json()

            # 调试输出查看完整的响应结构
            LOG.debug("Ollama 响应: {}", response_data)

            # 直接从响应数据中获取 content
            message_content = response_data.get("message", {}).get("content", None)
            if message_content:
                return message_content  # 返回生成的报告内容
            else:
                LOG.error("无法从响应中提取报告内容。")
                raise ValueError("Ollama API 返回的响应结构无效")
        except Exception as e:
            LOG.error(f"生成报告时发生错误：{e}")
            raise

if __name__ == '__main__':
    from config import Config  # 导入配置管理类
    config = Config()
    llm = LLM(config)

    markdown_content="""
# Progress for langchain-ai/langchain (2024-08-20 to 2024-08-21)

## Issues Closed in the Last 1 Days
- partners/chroma: release 0.1.3 #25599
- docs: few-shot conceptual guide #25596
- docs: update examples in api ref #25589
"""

    # 示例：生成 GitHub 报告
    system_prompt = "Your specific system prompt for GitHub report generation"
    github_report = llm.generate_report(system_prompt, markdown_content)
    LOG.debug(github_report)
