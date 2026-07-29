"""One-off script to seed the first admin user for a company, run once
against the client's Supabase instance before Phase 2's login cutover goes
live (there's no other way to get a first account into a fresh `users`
table). Reads DATABASE_URL from the environment - same variable
server/_db.py uses - so run this with the same env the deployed app has
(e.g. `vercel env pull` locally first).

Usage:
    DATABASE_URL=... python server/scripts/seed_admin.py \\
        --company garg_dental --username admin --full-name "Admin" --password "..."
"""
import argparse
import os
import sys

import bcrypt
import psycopg


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--company", required=True, help="companies.slug to seed the admin under, e.g. garg_dental")
    parser.add_argument("--username", required=True)
    parser.add_argument("--full-name", required=True)
    parser.add_argument("--password", required=True, help="Plaintext password, hashed before storage - never logged.")
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set.", file=sys.stderr)
        sys.exit(1)

    password_hash = bcrypt.hashpw(args.password.encode(), bcrypt.gensalt()).decode()

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("select id from companies where slug = %s", (args.company,))
            row = cur.fetchone()
            if row is None:
                print(f"No company with slug {args.company!r} - run the schema migration first.", file=sys.stderr)
                sys.exit(1)
            company_id = row[0]

            cur.execute("select 1 from users where company_id = %s and username = %s", (company_id, args.username))
            if cur.fetchone():
                print(f"A user named {args.username!r} already exists for {args.company!r}; not creating a duplicate.", file=sys.stderr)
                sys.exit(1)

            cur.execute(
                "insert into users (company_id, full_name, username, password_hash, role) "
                "values (%s, %s, %s, %s, 'admin') returning id",
                (company_id, args.full_name, args.username, password_hash),
            )
            new_id = cur.fetchone()[0]
        conn.commit()

    print(f"Created admin user {args.username!r} (id={new_id}) for company {args.company!r}.")


if __name__ == "__main__":
    main()
