"""List section details and available transformers without downloading a bill."""

from kseb_client import KSEBClient, KSEBClientError, KSEBValidationError


def main() -> None:
    consumer_no = input("Enter KSEB consumer number: ").strip()

    try:
        with KSEBClient() as client:
            captcha = client.get_transformer_captcha()
            image_path = "kseb_transformer_captcha.png"
            with open(image_path, "wb") as image_file:
                image_file.write(captcha.image)
            print(f"Captcha saved to {image_path}. Enter the characters shown there.")
            captcha_code = input("Captcha: ").strip()
            result = client.get_grid_capacity_options(
                consumer_no,
                captcha_code=captcha_code,
                unique_id=captcha.unique_id,
            )

        print(f"Section: {result.section.section}")
        print(f"Subdivision: {result.section.subdivision}")
        print(f"Division: {result.section.division}")
        print("\nAvailable transformers:")

        if not result.transformers:
            print("No transformers were returned for this section.")
            return

        for transformer in result.transformers:
            print(
                f"- {transformer.transformer_name}: "
                f"{transformer.balance_available:g} kW available "
                f"(allowed {transformer.allowed_cap:g}, "
                f"committed {transformer.comp_cap:g}, "
                f"registered {transformer.regi:g})"
            )

    except KSEBValidationError as error:
        print(f"Invalid input: {error}")
    except KSEBClientError as error:
        print(f"Could not retrieve grid capacity options: {error}")


if __name__ == "__main__":
    main()
