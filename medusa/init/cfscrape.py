# coding=utf-8
"""Shim for `cfscrape` to solve the challenge without Node.js."""
from __future__ import absolute_import
from __future__ import unicode_literals

import logging
import re
from base64 import b64encode

import cfscrape

import js2py

# Disallow parsing of the unsafe 'pyimport' statement in Js2Py.
js2py.disable_pyimport()


def patch_cfscrape():
    """Patch `cfscrape.CloudflareScraper.solve_challenge` to use Js2Py."""
    assert hasattr(cfscrape.CloudflareScraper, 'solve_challenge')
    cfscrape.CloudflareScraper.solve_challenge = _patched_solve_challenge


def _patched_solve_challenge(self, body, domain):
    try:
        javascript = re.search(r'\<script type\=\"text\/javascript\"\>\n(.*?)\<\/script\>',body, flags=re.S).group(1) # find javascript

        challenge, ms = re.search(
            r"setTimeout\(function\(\){\s*(var "
            r"s,t,o,p,b,r,e,a,k,i,n,g,f.+?\r?\n[\s\S]+?a\.value\s*=.+?)\r?\n"
            r"(?:[^{<>]*},\s*(\d{4,}))?",
            javascript, flags=re.S
        ).groups()

        # The challenge requires `document.getElementById` to get this content.
        # Future proofing would require escaping newlines and double quotes
        innerHTML = ''
        for i in javascript.split(';'):
            if i.strip().split('=')[0].strip() == 'k':      # from what i found out from pld example K var in
                k = i.strip().split('=')[1].strip(' \'')    #  javafunction is for innerHTML this code to find it
                innerHTML = re.search(r'\<div.*?id\=\"'+k+r'\".*?\>(.*?)\<\/div\>',body).group(1) #find innerHTML

        # Prefix the challenge with a fake document object.
        # Interpolate the domain, div contents, and JS challenge.
        # The `a.value` to be returned is tacked onto the end.
        challenge = """
            var document = {
                createElement: function () {
                    return { firstChild: { href: "http://%s/" } }
                },
                getElementById: function () {
                    return {"innerHTML": "%s"};
                }
                };
            %s; a.value
        """ % (
            domain,
            innerHTML,
            challenge,
        )
        # Encode the challenge for security while preserving quotes and spacing.
        challenge = b64encode(challenge.encode("utf-8")).decode("ascii")
        # Use the provided delay, parsed delay, or default to 8 secs
        delay = self.delay or (float(ms) / float(1000) if ms else 8)
    except Exception:
        raise ValueError('Unable to identify Cloudflare IUAM Javascript on website. %s' % cfscrape.BUG_REPORT)

    try:
        result = js2py.eval_js(challenge)
    except Exception:
        logging.error('Error executing Cloudflare IUAM Javascript. %s', cfscrape.BUG_REPORT)
        raise

    try:
        float(result)
    except Exception:
        raise ValueError('Cloudflare IUAM challenge returned unexpected answer. %s' % cfscrape.BUG_REPORT)

    return result, delay
