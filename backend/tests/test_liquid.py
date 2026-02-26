import liquid
import json

def test_liquid_rendering():
    template_html = """
    <html>
      <body>
        <h1>Hello {{ first_name | default: 'there' }}!</h1>
        <p>Welcome to {{ company }}.</p>
        {% if unsubscribe_link %}
          <a href="{{ unsubscribe_link }}">Unsubscribe</a>
        {% endif %}
      </body>
    </html>
    """
    
    test_cases = [
        {
            "name": "Full data",
            "data": {"first_name": "Alice", "company": "Antigravity", "unsubscribe_link": "http://unsub.com"}
        },
        {
            "name": "Missing first_name",
            "data": {"company": "Antigravity", "unsubscribe_link": "http://unsub.com"}
        },
        {
            "name": "Missing unsubscribe_link",
            "data": {"first_name": "Bob", "company": "Antigravity"}
        }
    ]
    
    print("--- Liquid Rendering Test ---")
    for case in test_cases:
        print(f"\nTest: {case['name']}")
        try:
            tmpl = liquid.Template(template_html)
            rendered = tmpl.render(**case['data'])
            print(f"Result:\n{rendered.strip()}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_liquid_rendering()
