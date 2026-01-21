from perplexity_scraper import pull_news_perplexity

if __name__ == "__main__":
    # batch scrape
    companies_list = [
        ("Partmax", "Melbourne"),
        ("GRC Solutions", "Sydney"),
        ("Smartsoft", "Adelaide"),
        ("OnQ Software", "Melbourne"),
        ("LAB Group", "Melbourne"),
        ("Axcelerate", "Brisbane"),
        ("Pharmako Biotechnologies", "Sydney"),
        ("iD4me", "Melbourne")
    ]

    for name, location in companies_list:
        pull_news_perplexity(name, location, "year")