from language_model_gateway.gateway.tools.url_to_markdown_tool import URLToMarkdownTool


async def test_url_to_markdown_tool_async() -> None:
    tool = URLToMarkdownTool()
    content, artifact = await tool._arun("https://www.example.com")
    print(content)
    assert "This domain is for use" in content


async def test_url_to_markdown_tool_complex_async() -> None:
    tool = URLToMarkdownTool()
    content, artifact = await tool._arun(
        "https://www.johnmuirhealth.com/doctor/David-Chang-MD/1174545909"
    )
    print(content)
    assert "John Muir" in content
