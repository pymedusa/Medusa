# coding=utf-8
"""Shim for `cfscrape` to solve the challenge without Node.js."""
from __future__ import absolute_import
from __future__ import unicode_literals

import logging
import re

import cfscrape
import js2py

# Disallow parsing of the unsafe 'pyimport' statement in Js2Py.
js2py.disable_pyimport()


def patch_cfscrape():
    assert hasattr(cfscrape.CloudflareScraper, 'solve_challenge')
    cfscrape.CloudflareScraper.solve_challenge = _patched_solve_challenge


def _patched_solve_challenge(self, body, domain):
    try:
        js, ms = re.search(
            r"setTimeout\(function\(\){\s*(var "
            r"s,t,o,p,b,r,e,a,k,i,n,g,f.+?\r?\n[\s\S]+?a\.value\s*=.+?)\r?\n"
            r"(?:[^{<>]*},\s*(\d{4,}))?",
            body,
        ).groups()

        # The challenge requires `document.getElementById` to get this content.
        # Future proofing would require escaping newlines and double quotes
        inner_html = re.search(r'<div(?: [^<>]*)? id="cf-dn.*?">([^<>]*)', body)
        inner_html = inner_html.group(1) if inner_html else ''

        # Prefix the challenge with a fake document object.
        # Interpolate the domain, div contents, and JS challenge.
        # The `a.value` to be returned is tacked onto the end.
        challenge = """
            var document = {
                createElement: function () {
                    return { firstChild: { href: "http://%s/" } };
                },
                getElementById: function () {
                    return {"innerHTML": "%s"};
                }
            };

            %s; a.value
        """ % (domain, inner_html, js)

        # Use the provided delay, parsed delay, or default to 8 secs
        delay = self.delay or (float(ms) / float(1000) if ms else 8)
    except Exception:
        raise ValueError('Unable to identify Cloudflare IUAM Javascript on website. %s' % cfscrape.BUG_REPORT)

    try:
        result = js2py.eval_js(challenge)
    except Exception:
        logging.error('Error executing Cloudflare IUAM Javascript. %s' % cfscrape.BUG_REPORT)
        raise

    try:
        float(result)
    except Exception:
        raise ValueError('Cloudflare IUAM challenge returned unexpected answer. %s' % cfscrape.BUG_REPORT)

    return result, delay
