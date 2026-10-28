"""Show section details and the consumer's transformer without downloading a bill."""

from kseb_client import KSEBClient, KSEBClientError, KSEBTurnstileError, KSEBValidationError


def main() -> None:
    consumer_no = input("Enter KSEB consumer number: ").strip()

    try:
        with KSEBClient() as client:
            print("Complete the Cloudflare check on https://wss.kseb.in/selfservices/reCap")
            turnstile_token = input("Turnstile token (cf-turnstile-response): ").strip()
            result = client.get_grid_capacity_options(consumer_no, turnstile_token=turnstile_token)

        print(f"Section: {result.section.section}")
        print(f"Subdivision: {result.section.subdivision}")
        print(f"Division: {result.section.division}")
        print("\nTransformer:")

        for transformer in result.transformers:
            print(
                f"- {transformer.transformer_name}: "
                f"{transformer.balance_available:g} kW available "
                f"(allowed {transformer.allowed_cap:g}, "
                f"connected {transformer.comp_cap:g}, "
                f"as on {transformer.as_on})"
            )

    except KSEBTurnstileError as error:
        print(error)
    except KSEBValidationError as error:
        print(f"Invalid input: {error}")
    except KSEBClientError as error:
        print(f"Could not retrieve grid capacity options: {error}")


if __name__ == "__main__":
    main()
