import requests
import json
import time

def fetch_substack_activity(initial_url):
    all_activities = []
    next_url = initial_url
    
    print("Starting fetch with no item limit. This may take a while...")

    while next_url:
        try:
            print(f"Fetching next batch of data...")
            response = requests.get(next_url)
            response.raise_for_status()
            
            data = response.json()

            if "items" in data and data["items"]:
                all_activities.extend(data["items"])
                print(f"Fetched {len(data['items'])} items. Total so far: {len(all_activities)}")
            else:
                print("\nReached the end of the feed. All items fetched.")
                break

            if "nextCursor" in data and data["nextCursor"]:
                base_url = initial_url.split('?')[0]
                cursor = data["nextCursor"]
                next_url = f"{base_url}?cursor={cursor}"
            else:
                print("\nReached the end of the feed. All items fetched.")
                next_url = None

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                print("\nRate limit hit (429). Pausing for 10 seconds before retrying...\n")
                time.sleep(10)
                continue
            else:
                print(f"An unexpected HTTP error occurred: {e}")
                break
        except requests.exceptions.RequestException as e:
            print(f"An error occurred during the request: {e}")
            break
        except json.JSONDecodeError:
            print(f"Failed to decode JSON from the response.")
            break
            
    return all_activities

def categorize_and_save_activity_as_markdown(activities, user_substack_url, filename="substack_activity.md"):

    notes = []
    articles = []
    quote_restacks = []
    
    print("\n--- Starting to parse fetched data ---")

    for i, activity in enumerate(activities):
        entity_key = activity.get("entity_key", "Unknown Key")
        activity_type = activity.get("type")
        
        print(f"\n[Item {i+1}/{len(activities)}] Processing entity: {entity_key} | Type: {activity_type}")

        if activity_type == "post" and activity.get("post"):
            post_data = activity.get("post", {})
            title = post_data.get("title", "No Title Provided")
            link = post_data.get("canonical_url")
            author = "Unknown Author"
            bylines = post_data.get("publishedBylines")
            if bylines and len(bylines) > 0:
                author = bylines[0].get("name", author)
            
            if link:
                print(f"  -> Identified as: Article. Saving to 'Articles'. Title: '{title}'")
                articles.append({"title": title, "author": author, "link": link})
            else:
                print("  -> SKIPPED: 'post' type with no link.")

        elif activity_type == "comment" and activity.get("comment"):
            comment_data = activity.get("comment", {})
            attachments = comment_data.get("attachments", [])
            original_post_data = None
            attachment_data = None 

            if attachments:
                for att in attachments:
                    if att.get("type") == "post" and att.get("post"):
                        original_post_data = att.get("post")
                        attachment_data = att
                        break

            if original_post_data:
                link = original_post_data.get("canonical_url")
                title = original_post_data.get("title", "No Title Provided")
                
                user_comment_text = (comment_data.get("body") or "").strip()
                
                selected_text = ""
                if attachment_data:
                    post_selection = attachment_data.get("postSelection")
                    if post_selection:
                        selected_text = (post_selection.get("text") or "").strip()
                
                quote_text = user_comment_text if user_comment_text else selected_text

                author = "Unknown Author"
                bylines = original_post_data.get("publishedBylines")
                if bylines and len(bylines) > 0:
                    author = bylines[0].get("name", author)

                if quote_text:
                    print(f"  -> Identified as: Quote Restack. Saving to 'Quote Restacks'.")
                    quote_restacks.append({"quote": quote_text, "link": link, "original_title": title})
                else:
                    print(f"  -> Identified as: Simple Restack. Saving to 'Articles'. Title: '{title}'")
                    articles.append({"title": title, "author": author, "link": link})
            
            else:
                text = (comment_data.get("body") or "").strip()
                comment_id = comment_data.get('id')
                link = f"{user_substack_url}/notes#details_{comment_id}" if comment_id else None
                
                if text and link:
                    print("  -> Identified as: User's original Note. Saving to 'Notes'.")
                    notes.append({"text": text, "link": link})
                else:
                    print("  -> SKIPPED: 'comment' with no text or attachments.")
        else:
            print("  -> SKIPPED: Unhandled activity type.")

    print("\n--- All items parsed. Writing to Markdown file... ---")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# Substack Activity for {user_substack_url.split('//')[1]}\n\n")
        f.write(f"*Total items processed: {len(activities)}*\n\n")

        if articles:
            f.write("## Articles & Restacks\n\n")
            for article in articles:
                f.write(f"**Title:** {article['title']}\n\n")
                f.write(f"**Author:** {article['author']}\n\n")
                f.write(f"**Link:** [{article['link']}]({article['link']})\n\n")
                f.write("---\n\n")

        if notes:
            f.write("## Notes\n\n")
            for note in notes:
                clean_text = note['text'].replace('<p>', '').replace('</p>', '\n\n').strip()
                f.write(f"> {clean_text}\n\n")
                f.write(f"**Link:** [{note['link']}]({note['link']})\n\n")
                f.write("---\n\n")

        if quote_restacks:
            f.write("## Quote Restacks\n\n")
            for restack in quote_restacks:
                f.write(f"**Original Title:** {restack['original_title']}\n\n")
                clean_quote = restack['quote'].replace('<p>', '').replace('</p>', '\n\n').strip()
                f.write(f"> {clean_quote}\n\n")
                f.write(f"**Link to article:** [{restack['link']}]({restack['link']})\n\n")
                f.write("---\n\n")
    print(f"--- Markdown file '{filename}' saved successfully! ---")


if __name__ == "__main__":
    username = ""
    initial_api_url = f"https://{username}.substack.com/api/v1/reader/feed/profile/218508520?cursor=eyJiZWZvcmVfdGltZXN0YW1wIjoiMjAyNS0wOC0yOFQyMjoxMjozNC4yODZaIiwiZW50aXR5X2tleSI6ImMtMTQ5NzQyMTU2IiwicGlubmVkX2VudGl0eV9rZXkiOm51bGwsImNvbnRleHRfdGltZXN0YW1wIjoiMjAyNS0wOC0yOFQwNToxODo0MC4wMzdaIiwicHJlcGVuZGVkX3Bvc3RfaWRzIjpudWxsLCJwYWdlX251bWJlciI6Mn0%3D"
    user_substack_url = f"https://{username}.substack.com"
    raw_output_filename = "raw_substack_data.json"
    processed_output_filename = "substack_activity.md"

    all_user_activity = fetch_substack_activity(initial_api_url)
    
    if all_user_activity:
        with open(raw_output_filename, 'w', encoding='utf-8') as f:
            json.dump(all_user_activity, f, ensure_ascii=False, indent=4)
        print(f"\nSuccessfully saved raw data to {raw_output_filename}")

        categorize_and_save_activity_as_markdown(all_user_activity, user_substack_url, filename=processed_output_filename)
    else:
        print("No activity was fetched.")
