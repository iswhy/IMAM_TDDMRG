import glob
import numpy as np
from pyscf import symm
from IMAM_TDDMRG.utils import util_extract
from IMAM_TDDMRG.observables import extract_time


def calc(rdm, mol=None, orb=None, corr_dm=False, inputs=None):
    
    '''
    Calculate static and dynamic correlation indices and optionally, correlation density 
    matrices (used for plotting the local correlations). If rdm is obtained from a state
    with some core orbitals (exactly doubly occupied), then matrix elements involving
    these orbitals may be omitted from rdm since their contributions to the correlation
    indices and density matrices are zero. When omitting core orbitals in the rdm, these
    orbitals must also be absent in orb.

    Input
    -----
    mol:
      Mole object describing the molecule. The information about AO basis is contained here.
    rdm: 
      One-particle reduced density matrix in orthonormal orbital basis representation 
      where these orbitals are given by orb. rdm should be spin-resolved, i.e. rdm[0,:,:]
      and rdm[1,:,:] must correspond to the RDMs in alpha and beta spin-orbitals.
    orb:
      AO coefficients of orthonormal orbitals in which rdm is represented.

    Output
    ------
    o_s:
      Natural spin-orbital contribution to the global static correlation index. To get
      the global static correlation index, simply sum over all of its elements.
    o_d:
      Same matrix as for o_s except that it is for dynamic correlation.
    corr_s:
      Static correlation density matrix, in 'AO reprsentation', which is the representation
      for any one-particle density matrix-like matrix that can directly be input to 
      pyscf.tools.cubegen.density function to plot its values in 3D space.
    corr_d:
      Same matrix as for corr_s except that it is for dynamic correlation.
    '''

    if mol is None:
        mol = util_extract.mole(inputs)
    if orb is None:
        orb = np.load(inputs['orb_path'])
        
    assert len(rdm.shape) == 3
    assert orb.shape[1] == rdm.shape[1]
    cpx = isinstance(rdm[0,0,0], complex)
    if cpx:
        dtype = complex
    else:
        dtype = float

    #==== Compute natural occupancies and orbitals ====#
    osym = symm.label_orb_symm(mol, mol.irrep_id, mol.symm_orb, orb)
    natocc = np.zeros((2,rdm.shape[2]), dtype=dtype)
    natorb = np.zeros(rdm.shape, dtype=dtype)
    for i in range(2):
        natocc[i,:], natorb[i,:,:] = symm.eigh(rdm[i,:,:], osym)
    natocc = natocc.real

    #==== Transform nat. orbitals from orb rep. to AO rep. ====#
    natorb = orb @ natorb

    #==== Calculate static and dynamic correlation indices ====#
    o_s = np.zeros(natocc.shape)
    o_d = np.zeros(natocc.shape)
    for i in range(2):
        o_s[i,:] = 0.50 * natocc[i,:]*(1-natocc[i,:])
        o_d[i,:] = 0.25 * ( np.sqrt(natocc[i,:]*(1-natocc[i,:])) -
                            2*natocc[i,:]*(1-natocc[i,:]) )

    #==== Calculate static and dynamic correlation density matrices ====#
    if corr_dm:
        corr_s = np.zeros(natorb.shape[1:3], dtype=dtype)
        corr_d = np.zeros(natorb.shape[1:3], dtype=dtype)
        for i in range(2):
            corr_s = corr_s + (natorb * o_s[i,:]) @ natorb.conj().T     # natorb @ o_s @ natorb.H
            corr_d = corr_d + (natorb * o_d[i,:]) @ natorb.conj().T     # natorb @ o_d @ natorb.H
    else:
        corr_s = corr_d = None

    return o_s, o_d, corr_s, corr_d



def td_calc(mol=None, tdir=None, orb=None, corr_dm=False, nc=(30,30,30), outfile='corr_id',
            simtime_thr=1E-11, inputs=None):

    if mol is None:
        mol = util.extract_mole(inputs)
    if orb is None:
        orb = np.load(inputs['orb_path'])
    if tdir is None:
        tdir = inputs['te_sample']

    #==== Construct the time array ====#
    if isinstance(tdir, list):
        tevo_dir = tdir.copy()
    elif isinstance(tdir, tuple):
        tevo_dir = tdir
    elif isinstance(tdir, str):
        tevo_dir = tuple( [tdir] )
    tt = []
    for d in tevo_dir:
        tt = np.hstack( (tt, extract_time.get(d)) )  # tt may contains identical time points.
    idsort = np.argsort(tt)
    ntevo = 1
    for i in range(1,len(tt)):
        if tt[i]-tt[i-1] > simtime_thr: ntevo += 1 
    ndigit = len(str(ntevo))

    #==== Get 1RDM path names ====#
    rdm_dir = []
    for d in tevo_dir:
        rdm_dir = rdm_dir + glob.glob(d + '/tevo-*')

    #==== Print column titles ====#
    with open(outfile, 'w') as outf:
        outf.write('#%9s %13s  ' % ('Col #1', 'Col #2'))
        outf.write(' %16s %16s' % ('Col #3', 'Col #4'))
        outf.write('\n')
        outf.write('#%9s %13s  ' % ('No.', 'Time (fs)'))
        outf.write(' %16s %16s' % ('Static id.', 'Dynamic id.'))
        outf.write('\n')

    k = 0
    kk = 0
    for i in idsort:
        if kk > 0:
            assert not (tt[i] < t_last), 'Time points are not properly sorted, this is ' \
                'a bug in the program. Report to the developer. ' + \
                f'Current time point = {tt[i]:13.8f}.'
        #==== When the time point is different from the previous one ====#
        if (kk > 0 and tt[i]-t_last > simtime_thr) or kk == 0:
            rdm = np.load(rdm_dir[i] + '/1pdm.npy')
            echeck = np.linalg.eigvalsh(np.sum(rdm, axis=0))
            o_s, o_d, corr_s, corr_d = calc(mol, rdm, orb, corr_dm)
            i_s = np.sum(o_s)
            i_d = np.sum(o_d)

            #==== Print correlation indices ====#
            with open(outfile, 'a') as outf:
                #== Print time ==#
                outf.write(' %9d %13.8f  ' % (k, tt[i]))
    
                #== Print correlation indices ==#
                outf.write(' %16.6e %16.6e' % (i_s, i_d))
                outf.write('\n')

            #==== Cube-print local correlation functions ====#
            if corr_dm:
                assert corr_s is not None and corr_d is not None
                cubename = rdm_dir[i] + '/corr-s' + str(k).zfill(ndigit) + '.cube'
                cubegen.density(mol, cubename, corr_s, nx=nc[0], ny=nc[1], nz=nc[2])
                cubename = rdm_dir[i] + '/corr-d' + str(k).zfill(ndigit) + '.cube'
                cubegen.density(mol, cubename, corr_d, nx=nc[0], ny=nc[1], nz=nc[2])

            #==== Increment unique time point index ====#
            k += 1

        #==== When the time point is similar to the previous one ====#
        elif kk > 0 and tt[i]-t_last < simtime_thr:
            util_print.print_warning\
                ('The data loaded from \n    ' + rdm_dir[i] + '\nhas a time point almost ' +
                 'identical to the previous time point. Duplicate time point = ' +
                 f'{tt[i]:13.8f}')
            rdm = np.load(rdm_dir[i] + '/1pdm.npy')
            echeck_tsim = np.linalg.eigvalsh(np.sum(rdm, axis=0))
            if max(np.abs(echeck_tsim - echeck)) > 1E-6:
                util_print.print_warning\
                    (f'The 1RDM loaded at the identical time point {tt[i]:13.8f} yields ' +
                     'eigenvalues different by more than 1E-6 as the other identical \n' +
                     'time point. Ideally you don\'t want to have such inconcsistency ' +
                     'in your data. Proceed at your own risk.')

        t_last = tt[i]

        #==== Increment general (non-unique) time point index ====#
        kk += 1
