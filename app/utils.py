async def model_to_dict(model_instance):
    """
    Recursively converts a Model instance into a dictionary.
    """
    if hasattr(model_instance, "_ossapi_data"):
        result = {}
        for key, value in model_instance._ossapi_data.items():
            if hasattr(value, "_ossapi_data"):  # If value is a Model instance
                result[key] = await model_to_dict(value)
            else:
                result[key] = value
        return result
    raise TypeError(f"Object {model_instance} is not a valid Model instance.")
