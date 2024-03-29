import numpy as np
import scipy.linalg
from pyscf import scf, symm, lo
from IMAM_TDDMRG.utils.util_print import print_matrix



##########################################################################
def sort_orbs(orbs, occs, ergs, sr='erg', s='de'):
    '''
    Sort occs, orbs, and ergs based on the elements of occs or ergs.
    '''

    assert isinstance(occs, np.ndarray) or occs is None
    assert isinstance(ergs, np.ndarray) or ergs is None

    
    assert sr == 'erg' or sr == 'occ', \
        'sort_orbs: The value of the argument \'sr\' can only either ' + \
        'be \'erg\' or \'occ\'. Its current value: sr = ' + sr + '.'
    assert s == 'de' or s == 'as', \
        'sort_orbs: The value of the argument \'s\' can only either ' + \
        'be \'de\' or \'as\'. Its current value: s = ' + s + '.'

    if sr == 'erg' and ergs is None:
        raise ValueError('sort_orbs: If sr = \'erg\', then ergs must ' + \
                         'not be None.')
    if sr == 'occ' and occs is None:
        raise ValueError('sort_orbs: If sr = \'occ\', then occs must ' + \
                         'not be None.')

    if s == 'de':       # Descending
        if sr == 'erg': isort = np.argsort(-ergs)
        if sr == 'occ': isort = np.argsort(-occs)
    elif s == 'as':     # Ascending
        if sr == 'erg': isort = np.argsort(ergs)
        if sr == 'occ': isort = np.argsort(occs)
    
    if occs is not None: occs = occs[isort]
    if ergs is not None: ergs = ergs[isort]
    orbs = orbs[:,isort]

    return orbs, occs, ergs
##########################################################################


##########################################################################
def sort_similar(orb, orb_ref, ovl=None, similar_thr=0.8, dissim_break=False, verbose=1):
    '''
    orb: Orbitals to be sorted in AO basis.
    orb_ref: Orbitals in AO basis whose ordering is used as reference for the sorting.
    '''
    
    assert orb.shape[0] == orb_ref.shape[0]
    assert orb.shape[1] == orb_ref.shape[1]
    
    n = orb.shape[0]
    if ovl is None:
        ovl = np.eye(n,n)
        
    ovl_ref = orb_ref.T @ ovl @ orb
    if verbose == 1:
        print('Overlap matrix between the calculated (column) and reference (row) orbitals:')
        print_matrix(ovl_ref)
        
    idmax = [np.argmax(np.abs(ovl_ref[:,i])) for i in range(0, ovl_ref.shape[1])]
    idmax = np.array(idmax)
    #OLDassert len(idmax) == len(set(idmax)), 'Some orbitals have conflicting orders. ' + \
    #OLD    f'ID of the maximum of each column: {idmax}'
    elmax = [np.max(np.abs(ovl_ref[:,i])) for i in range(0, ovl_ref.shape[1])]
    elmax = np.array(elmax)
    dissim = idmax[elmax < similar_thr]
    if len(dissim) > 0:
        if dissim_break:
            raise ValueError('These calculated orbitals: {str(dissim+1)} are ' + \
                             'too dissimilar to the reference orbitals.')
        else:
            print(f'WARNING: These calculated orbitals: {str(dissim+1)} are too ' + \
                  'dissimilar to the reference orbitals.')
    
    # Reorder columns of orb such that if ovl_ref is recalculated using the newly
    # ordered orb, the maximum of each column of ovl_ref is a diagonal element.
    idsort = np.argsort(idmax)

    return idsort
##########################################################################


##########################################################################
##########################################################################
def sort_irrep(mol, orb, irrep=None):

    osym = symm.label_orb_symm(mol, mol.irrep_name, mol.symm_orb, orb)
    symset = set(osym)
    if irrep is not None:
        assert len(irrep) == len(set(irrep))
        for i in range(0,len(irrep)):
            assert irrep[i] in symset
        symset = irrep
            
    idsort = []
    for s in symset:
        idsort = idsort + [i for i in range(0,len(osym)) if osym[i]==s]
    idsort = np.array(idsort)
    
    return idsort
##########################################################################


