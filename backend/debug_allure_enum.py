from allure_commons.types import AttachmentType
import json

def debug_enum():
    print(f"AttachmentType.PNG value: {AttachmentType.PNG.value}")
    print(f"Type of value: {type(AttachmentType.PNG.value)}")

if __name__ == "__main__":
    debug_enum()
