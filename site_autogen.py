import argparse
import json
import os
import re
import sys
import shutil


from jinja2 import (
     Environment,
     FileSystemLoader,
     Markup,
     select_autoescape,
     )
from livereload import Server
from markdown import Markdown


def create_jinja_env(templates_path):
    return Environment(
           loader=FileSystemLoader(templates_path),
           autoescape=select_autoescape(['html', 'xml']),
    )


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-md', '--md_root',
                        type=check_dirpath,
                        required=True,
                        help='path to the root to take markdown files')
    parser.add_argument('-hr', '--html_root',
                        type=check_dirpath,
                        required=True,
                        help='path to the root to save the generated html')
    parser.add_argument('-t', '--templates',
                        type=check_dirpath,
                        required=True,
                        help='path to the jinja templates')
    parser.add_argument('-st', '--static',
                        type=check_dirpath,
                        required=True,
                        help='path to the static files')
    parser.add_argument('-c', '--json_conf',
                        type=argparse.FileType(mode='r'),
                        required=True,
                        help="config.json of the site's articles structer")
    return parser


def check_dirpath(dirpath):
    if not os.path.exists(dirpath):
        raise argparse.ArgumentTypeError("{} does not exists".format(dirpath))
    return dirpath


def create_article_html(article_context, j2_env,
                        md_root, templ='article.html'):
    article_markdown = load_article_md(md_root, article_context['source'])
    article_markup = Markup(Markdown().convert(article_markdown))
    return j2_env.get_template(templ).render(
                                            article_markup=article_markup,
                                            article_context=article_context,
                                            )


def create_index_html(site_context, j2_env, templ='index.html'):
    return j2_env.get_template(templ).render(articles=site_context)


def collect_static_files_for_site(static, html_root):
    shutil.copytree(static, os.path.join(html_root, static))


def create_relative_url(source):
    source = source.replace('.md', '.html')
    return re.sub(r'\w+_', '', source)


def generate_site_from_markdown(md_root, html_root, json_conf, j2_env, static):
    site_context = make_site_context(json_conf)
    index_html = create_index_html(site_context, j2_env)
    shutil.rmtree(html_root)
    save_index_html_to_rootdir(index_html, html_root)
    for article_context in site_context:
        article_html = create_article_html(article_context, j2_env, md_root)
        save_article_html_in_dir(article_html, article_context, html_root)
    collect_static_files_for_site(static, html_root)


def load_site_config(file_handler, start=0):
    file_handler.seek(start)  # for server reload make_site
    return json.load(file_handler)


def load_article_md(md_root, source_md):
    with open(os.path.join(md_root, source_md), 'r') as file_handler:
        return file_handler.read()


def make_site():  # wrap generate_site_from_markdown for use in server.watch
    generate_site_from_markdown(
            md_root=namespace.md_root,
            html_root=namespace.html_root,
            json_conf=namespace.json_conf,
            j2_env=create_jinja_env(namespace.templates),
            static=namespace.static,
            )


def make_site_context(json_conf):
    site_config = load_site_config(json_conf)
    topics_list_of_dicts = site_config['topics']
    articles_list_of_dicts = site_config['articles']
    for article in articles_list_of_dicts:
        for topic in topics_list_of_dicts:
            if article['topic'] in topic['slug']:
                article['topic_ru'] = topic['title']
        article['rel_url'] = create_relative_url(article['source'])
    return articles_list_of_dicts


def save_index_html_to_rootdir(index_html, html_root):
    if not os.path.exists(html_root):
        os.mkdir(html_root)
    with open(os.path.join(html_root, 'index.html'), 'w') as file_handler:
            file_handler.write(index_html)


def save_article_html_in_dir(article_html, article_context, html_root):
    article_path = article_context['rel_url']
    article_dir = os.path.join(html_root, os.path.dirname(article_path))
    if not os.path.exists(article_dir):
        os.mkdir(article_dir)
    with open(os.path.join(html_root, article_path), 'w') as file_handler:
        file_handler.write(article_html)


if __name__ == '__main__':
    parser = create_parser()
    namespace = parser.parse_args(sys.argv[1:])
    make_site()
    server = Server()
    server.watch(namespace.templates, make_site)
    server.serve(root=namespace.html_root)
