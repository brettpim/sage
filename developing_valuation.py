# -*- coding: utf-8 -*-
r"""
Valuations on polynomial rings based on `\phi`-adic expansions

This file implements a base class for discrete valuations on polynomial rings,
defined by a `\phi`-adic expansion.

AUTHORS:

- Julian Rueth (15-04-2013): initial version

"""
#*****************************************************************************
#       Copyright (C) 2013-2016 Julian Rüth <julian.rueth@fsfe.org>
#
#  Distributed under the terms of the GNU General Public License (GPL)
#  as published by the Free Software Foundation; either version 2 of
#  the License, or (at your option) any later version.
#                  http://www.gnu.org/licenses/
#*****************************************************************************

# Fix doctests so they work in standalone mode (when invoked with sage -t, they run within the mac_lane/ directory)
import sys, os
if hasattr(sys.modules['__main__'], 'DC') and 'standalone' in sys.modules['__main__'].DC.options.optional:
    sys.path.append(os.getcwd())
    sys.path.append(os.path.dirname(os.getcwd()))

from valuation import DiscretePseudoValuation
from sage.misc.abstract_method import abstract_method

from sage.misc.cachefunc import cached_method

def _lift_to_maximal_precision(c):
    r"""
    Lift ``c`` to maximal precision if the parent is not exact.

    EXAMPLES::

        sage: from sage.rings.padics.developing_valuation import _lift_to_maximal_precision
        sage: R = Zp(2,5)
        sage: x = R(1,2); x
        1 + O(2^2)
        sage: _lift_to_maximal_precision(x)
        1 + O(2^5)

        sage: x = 1
        sage: _lift_to_maximal_precision(x)
        1

    """
    return c if c.parent().is_exact() else c.lift_to_precision()

class DevelopingValuation(DiscretePseudoValuation):
    r"""
    Abstract base class for a discrete valuation of polynomials defined over
    the polynomial ring ``domain`` by the `\phi`-adic development.

    EXAMPLES::

        sage: from mac_lane import * # optional: standalone
        sage: R.<x> = QQ[]
        sage: v = GaussValuation(R, pAdicValuation(QQ, 7))

    TESTS::

        sage: TestSuite(v).run()

    """
    def __init__(self, parent, phi):
        r"""
        TESTS::

            sage: from mac_lane import * # optional: standalone
            sage: R.<x> = QQ[]
            sage: v = GaussValuation(R, pAdicValuation(QQ, 7))
            sage: isinstance(v, DevelopingValuation)

        """
        domain = parent.domain()
        from sage.rings.polynomial.polynomial_ring import is_PolynomialRing
        if not is_PolynomialRing(domain):
            raise TypeError("domain must be a polynomial ring but %r is not"%(domain,))
        if not domain.ngens() == 1:
            raise NotImplementedError("domain must be a univariate polynomial ring but %r is not"%(domain, ))

        phi = domain.coerce(phi)
        if phi.is_constant() or not phi.is_monic():
            raise ValueError("phi must be a monic non-constant polynomial but %r is not"%(phi,))

        DiscretePseudoValuation.__init__(self, parent)
        self._phi = phi

    def phi(self):
        r"""
        Return the polynomial `\phi`, the key polynomial of this valuation.

        EXAMPLES::

            sage: R = Zp(2,5)
            sage: S.<x> = R[]
            sage: v = GaussValuation(S)
            sage: v.phi()
            (1 + O(2^5))*x

        """
        return self._phi

    def effective_degree(self, f):
        r"""
        Return the effective degree of ``f`` with respect to this valuation.

        The effective degree of `f` is the largest `i` such that the valuation
        of `f` and the valuation of `f_i\phi^i` in the development `f=\sum_j
        f_j\phi^j` coincide (see [ML1936'] p.497.)

        INPUT:

        - ``f`` -- a non-zero polynomial in the domain of this valuation

        EXAMPLES::

            sage: R = Zp(2,5)
            sage: S.<x> = R[]
            sage: v = GaussValuation(S)
            sage: v.effective_degree(x)
            1
            sage: v.effective_degree(2*x + 1)
            0

        """
        f = self.domain().coerce(f)

        if f.is_zero():
            raise ValueError("the effective degree is only defined for non-zero polynomials")

        v = self(f)
        return [i for i,w in enumerate(self.valuations(f)) if w == v][-1]

    def coefficients(self, f):
        r"""
        Return the `\phi`-adic expansion of ``f``.

        INPUT:

        - ``f`` -- a monic polynomial in the domain of this valuation

        OUTPUT:

        An iterator `[f_0,f_1,\dots]` of polynomials in the domain of this
        valuation such that `f=\sum_i f_i\phi^i`

        EXAMPLES::

            sage: R = Qp(2,5)
            sage: S.<x> = R[]
            sage: v = GaussValuation(S)
            sage: f = x^2 + 2*x + 3
            sage: list(v.coefficients(f)) # note that these constants are in the polynomial ring
            [1 + 2 + O(2^5), 2 + O(2^6), 1 + O(2^5)]
            sage: v = v.extension( x^2 + x + 1, 1)
            sage: list(v.coefficients(f))
            [(1 + O(2^5))*x + 2 + O(2^5), 1 + O(2^5)]

        """
        if f.parent() is not self.domain():
            raise ValueError("f must be in the domain of the valuation")

        if self.phi().degree() == 1:
            from itertools import imap
            return imap(f.parent(), f(self.phi().parent().gen() - self.phi()[0]).coefficients(sparse=False))
        else:
            return self.__coefficients(f)

    def __coefficients(self, f):
        r"""
        Helper method for :meth:`coefficients` to create an iterator if `\phi`
        is not linear.

        INPUT:

        - ``f`` -- a monic polynomial in the domain of this valuation

        OUTPUT:

        An iterator `[f_0,f_1,\dots]` of polynomials in the domain of this
        valuation such that `f=\sum_i f_i\phi^i`

        EXAMPLES::

            sage: R = Qp(2,5)
            sage: S.<x> = R[]
            sage: v = GaussValuation(S)
            sage: v = v.extension( x^2 + x + 1, 1)
            sage: f = x^2 + 2*x + 3
            sage: list(v.coefficients(f)) # indirect doctest
            [(1 + O(2^5))*x + 2 + O(2^5), 1 + O(2^5)]
        """
        while f.degree() >= 0:
            f,r = self.__quo_rem(f)
            yield r

    def __quo_rem(self, f):
        qr = [ self.__quo_rem_monomial(i) for i in range(f.degree()+1) ]
        q = [ f[i]*g for i,(g,_) in enumerate(qr) ]
        r = [ f[i]*h for i,(_,h) in enumerate(qr) ]
        return sum(q), sum(r)

    @cached_method
    def __quo_rem_monomial(self, degree):
        f = self.domain().one() << degree
        return f.quo_rem(self.phi())

    def newton_polygon(self, f):
        r"""
        Return the newton polygon the `\phi`-adic development of ``f``.

        INPUT::

        - ``f`` -- a polynomial in the domain of this valuation

        EXAMPLES::

            sage: R = Qp(2,5)
            sage: S.<x> = R[]
            sage: v = GaussValuation(S)
            sage: f = x^2 + 2*x + 3
            sage: v.newton_polygon(f)
            Newton Polygon with vertices [(0, 0), (2, 0)]

            sage: v = v.extension( x^2 + x + 1, 1)
            sage: v.newton_polygon(f)
            Newton Polygon with vertices [(0, 0), (1, 1)]
            sage: v.newton_polygon( f * v.phi()^3 )
            Newton Polygon with vertices [(0, +Infinity), (3, 3), (4, 4)]

        .. SEEALSO::

            :class:`newton_polygon.NewtonPolygon`

        """
        if f.parent() is not self.domain():
            raise ValueError("f must be in the domain of the valuation")

        from sage.geometry.newton_polygon import NewtonPolygon
        return NewtonPolygon(enumerate(self.valuations(f)))

    def _call_(self, f):
        r"""
        Evaluate this valuation at ``f``.

        INPUT::

        - ``f`` -- a polynomial in the domain of this valuation

        EXAMPLES::

            sage: R = Qp(2,5)
            sage: S.<x> = R[]
            sage: v = GaussValuation(S)
            sage: f = x^2 + 2*x + 3
            sage: v(f)
            0

            sage: v = v.extension( x^2 + x + 1, 1)
            sage: v(f)
            0
            sage: v(f * v.phi()^3 )
            3
            sage: v(S.zero())
            +Infinity

        """
        if f.parent() is not self.domain():
            raise ValueError("f must be in the domain of the valuation %s but is in %s"%(self.domain(),f.parent()))

        if f.is_zero():
            from sage.rings.all import infinity
            return infinity

        return min(self.valuations(f))

    @abstract_method
    def valuations(self, f):
        pass

    def _repr_(self):
        r"""
        Return a printable representation of this valuation.

        EXAMPLES::

            sage: R = Qp(2,5)
            sage: S.<x> = R[]
            sage: from sage.rings.padics.developing_valuation import DevelopingValuation
            sage: DevelopingValuation(S, x)
            `(1 + O(2^5))*x`-adic valuation of Univariate Polynomial Ring in x over 2-adic Field with capped relative precision 5

        """
        return "`%s`-adic valuation of %s"%(self._phi, self.domain())

    def _make_monic_integral(self, G):
        if G.is_monic() and self(G) >= 0:
            return G
        raise NotImplementedError("The polynomial %r is not monic integral and %r does not provide the means to rewrite it to a monic integral polynomial."%(G, self))

    def _test_effective_degree(self, **options):
        r"""
        Test the correctness of :meth:`effective_degree`.

        EXAMPLES::

            sage: R = Zp(2,5)
            sage: S.<x> = R[]
            sage: v = GaussValuation(S)
            sage: v._test_effective_degree()
        
        """
        tester = self._tester(**options)
        S = tester.some_elements(self.domain().base_ring().some_elements())
        for x in S:
            if x == 0:
                continue
            tester.assertEqual(self.effective_degree(x), 0)

