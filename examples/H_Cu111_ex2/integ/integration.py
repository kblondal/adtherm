#!/usr/bin/env python3

#from scipy import integrate
import numpy as np
#from scipy import random
import generate_random_positions
import system as syst
import os, sys

#Declare a class for Adsorbates
class Adsorbate:

        def __init__(self):
                #define physical constants
                self.kB = 1.380649e-23 #Boltzmann constant in J/K
                self.h = 6.62607e-34 #Planck's constant in J*s
                self.c = 2.99792458e8 #speed of light in m/s
                #units we will need
                self.kJ = 6.241509125883258e+21 #eV per kJ

#List of subroutines
def q_analytical(adsorbate,T):
    '''A function that takes in value/array T and reduced mass of oscillating fragment nu and returns the analytical 1D H.O partition function.'''
    kB = adsorbate.kB
    h = adsorbate.h
    c = adsorbate.c
    ads_freq = np.array(adsorbate.frequencies)
    adsorbate.nu = ads_freq*c*1e2 #change from cm-1 units to Hz
    nu = adsorbate.nu
    if isinstance(nu, float): #for 1D
        q = kB*T/nu/h
    elif len(nu)==1: #also for 1D
        q = kB*T/nu/h
    elif len(nu)==3: #for adsorbed atom
        q = (kB*T/h)/nu
        q = np.prod(q)
    elif len(nu)==5: #for adsorbed linear molecule
        q = (kB*T/h)/nu
        q = np.prod(q)
    elif len(nu)==6: #for adsorbed non-linear molecule
        q = (kB*T/h)/nu #classical
        q = np.prod(q)
    return q

def V3D(adsorbate,ads): #analytical potential for testing the integration routine
    '''Takes in the force constant and displacement from equilibrium position. Returns the analytical potential of a 3D H.O.'''
    c = adsorbate.c
    ads_freq = np.array(adsorbate.frequencies)
    adsorbate.nu = ads_freq*c*1e2 #change from cm-1 units to Hz
    nu = adsorbate.nu
    k = adsorbate.mu*(2.0*np.pi*adsorbate.nu)**2.0 #units N/m or kg/s^2
    x = adsorbate.x-ads.COM[0]*1.0e-10
    y = adsorbate.y-ads.COM[1]*1.0e-10
    z = adsorbate.z-ads.COM[2]*1.0e-10
    adsorbate.pot_E_J = k[0]/2.0*x**2.0+k[1]/2.0*y**2.0+k[2]/2.0*z**2.0
    return adsorbate.pot_E_J

def P3D(adsorbate,T):
    '''Returns the Boltzmann factor of a 3D H.O.'''
    kB = adsorbate.kB
    return np.exp(-adsorbate.pot_E_J/(kB*T))

def q_2Dgas_zHO(adsorbate,T,ads):
    '''Returns the partition function of a free translator (for xy), with the z d.o.f. modeled as a H.O.'''
    kB = adsorbate.kB
    h = adsorbate.h
    c = adsorbate.c
    mu = adsorbate.mu
    ads_freq = np.array(adsorbate.frequencies)
    adsorbate.nu = ads_freq*c*1e2 #change from cm-1 units to Hz
    nu = adsorbate.nu
    k = adsorbate.mu*(2.0*np.pi*adsorbate.nu)**2.0
    A=(ads.x_boundaries[1]-ads.x_boundaries[0])*(ads.y_boundaries[1]-ads.y_boundaries[0])*((1e-10)**2.0)
    q_2D=(2.0*np.pi*mu*kB*T)/(h**2.0)*A
    q_z_quantum = 1.0/(1.0-np.exp(-h*nu[2]/(kB*T)))
    q_2Dgas = q_2D*q_z_quantum
    return q_2Dgas

def PG_corr_3D(adsorbate,T):
    '''Returns the harmonic Pitzer-Gwinn corrected that is the multiplicative quantum correction (including ZPE shift)
    for the classical PSI partition function.'''
    kB = adsorbate.kB
    h = adsorbate.h
    c = adsorbate.c
    ads_freq = np.array(adsorbate.frequencies)
    adsorbate.nu = ads_freq*c*1e2 #change from cm-1 units to Hz
    nu = adsorbate.nu
    q_class = (kB*T/h)/nu
    q_class = np.prod(q_class)
    q_quantum = 1.0/(1.0-np.exp(-h*nu/(kB*T))) #Zero of energy defined at ground state (=ZPE)
    q_quantum = np.prod(q_quantum)
    return q_quantum/q_class

def PG_transfer_direct(adsorbate,T):
    '''Harmonic PG correction for direct evaluation of S, dH and Cp. Takes the derivative of the log of the ratio of quantum to classical H.O. and applies to another classical function.
    '''
    kB = adsorbate.kB
    h = adsorbate.h
    c = adsorbate.c
    ads_freq = np.array(adsorbate.frequencies)
    adsorbate.nu = ads_freq*c*1e2 #change from cm-1 units to Hz
    nu = adsorbate.nu
    k = adsorbate.mu*(2.0*np.pi*adsorbate.nu)**2.0 #units N/m or kg/s^2
    q_class = (kB*T/h)/nu
    q_quantum = 1.0/(1.0-np.exp(-h*nu/(kB*T)))
    e_class = (kB*T/h)/nu*0.5 #result of kinetic factor * gaussian integral 1/2kx^2/kBT*exp(1/2kx^2/kBT)
    e_class_3vals = np.divide(e_class,q_class)
    e_class = np.sum(e_class_3vals) #additive for thermo quantities
    e_quantum = h*nu/(kB*T)*np.exp(h*nu/(kB*T))/(np.exp(h*nu/(kB*T))-1.0)**2.0 #result of sum over energy levels n of hvn/kBTexp(hvn)/kBT)
    e_quantum_3vals = np.divide(e_quantum,q_quantum) 
    e_quantum = np.sum(e_quantum_3vals)
    ZPE = np.sum(nu*h/2.0)/(kB*T)
    ZPE_shift = 1.0/np.exp(-ZPE)
    return q_quantum, q_class, e_quantum, e_class, e_quantum_3vals, e_class_3vals, ZPE, ZPE_shift

def PG_squared_direct(adsorbate,T):
    '''Harmonic quantum correction for direct evaluation of Cp. Takes the 2nd derivative of the log of the ratio of quantum to classical H.O. and applies to another classical funcion.
    ''' 
    kB = adsorbate.kB
    h = adsorbate.h
    c = adsorbate.c
    ads_freq = np.array(adsorbate.frequencies)
    adsorbate.nu = ads_freq*c*1e2 #change from cm-1 units to Hz
    nu = adsorbate.nu
    q_class = (kB*T/h)/nu
    q_quantum = 1.0/(1.0-np.exp(-h*nu/(kB*T)))
    e_squared_class = (kB*T/h)/nu*0.75#result of gaussian integral 1/4k^2x^4/kB^2T^2*exp(1/2kx^2/kBT)
    e_squared_class = np.divide(e_squared_class,q_class)
    e_squared_class = np.sum(e_squared_class) #additive for thermo quantities
    e_squared_quantum = (h*nu)**2.0/(kB*T)**2.0*np.exp(h*nu/(kB*T))*(np.exp(h*nu/(kB*T))+1.0)/(np.exp(h*nu/(kB*T))-1.0)**3.0 #result of sum over energy levels n of (hvn/kBT)^2exp(hvn/kBT)
    e_squared_quantum = np.divide(e_squared_quantum,q_quantum)
    e_squared_quantum = np.sum(e_squared_quantum)
    return e_squared_quantum, e_squared_class

########################################################################################
#SPECIFIC FOR THIS CASE - Depends on the type of surrogate model used
#This is the one used for H_Cu111_ex2
from mp_nn import MPoint, eval_mmodel
import torch

def V_pytorch(adsorbate, models, mpts):
    #Evaluate the surrogate
    #The model gives the relative energy (minimum energy = 0)
    kJ = adsorbate.kJ
    rhombus_coord=[adsorbate.x, adsorbate.y, adsorbate.z] #new model takes in x,y,z instead of z,x,y
    rhombus_coord=np.array(rhombus_coord)*1.e10 #convert back from m2 to angstroms
    rhombus_coord=rhombus_coord.flatten()
    pot_E=eval_mmodel(rhombus_coord, models, mpts, eps=0.02)
    pot_E_J=pot_E/kJ*1e3 #convert eV to joules
    adsorbate.pot_E_J=pot_E_J
    return adsorbate.pot_E_J

center = np.array([1.29399834, 0.74710724, 0.91696773])
hess =  np.array([[ 1.6849596, 0.00408805, -0.00514221],
 [ 0.00408805, 1.68520386, 0.05403173],
 [-0.00514221, 0.05403173, 3.08849911]])
yshift = 0.0
pt1 = MPoint(center, hess, yshift)

center = np.array([2.58798492, 1.49419989, 0.92222111])
hess = np.array([[ 1.72841124e+00, -1.01365742e-02, -7.82065304e-02],
 [-1.01365742e-02, 1.70989930e+00, -2.56467540e-03],
 [-7.82065304e-02, -2.56467540e-03, 3.22044812e+00]])
yshift = 0.000833212572616
pt2 = MPoint(center, hess, yshift)

mpts = [pt1, pt2]

# Load the torch models
model1 = torch.load('model_0.pth')
model2 = torch.load('model_1.pth')
models = [model1, model2]

##########################################################################################

def q_MCsampling(adsorbate, surf, ads, METHOD, T_array):
    '''A function that returns the MC-PSI parition funciton.'''
    h = adsorbate.h 
    kB = adsorbate.kB
    mu = adsorbate.mu
    kJ = adsorbate.kJ
    
    #Initialize 
    job_index = []
    too_close_index= []
    potential_array = []
    dz_array = []
    dx_array = []
    dy_array = []
    gamma_array =[]        
    coordfile=open('coord.txt', 'w') 
    energyfile=open('energies.txt', 'w')
    min_cutoff = 0.05 #minimum allowed distance between the adsorbate and surface atoms in angstroms
    max_cutoff = 100.0 #maximum allowed distance between the adsorbate and surface atoms in angstroms  
    integral = np.zeros(len(T_array)) #0.0
    int_E_integral = np.zeros(len(T_array))
    squared_int_E_integral=np.zeros(len(T_array))
    conv_param = 0.1 
    points_needed = 0
    points_not_valid = 0
    print("integration starting...")
    #TODO:specify a maximum number of integration points? 
    while conv_param > adsorbate.q_accuracy:# and points_needed<3000:
        ads.N_values = 1
        generate_random_positions.manipulate_ads(ads, METHOD)
        #rotate and translate the adsorbate
        #syst.rotate_COM(ads,0)
        syst.translate(ads,0,0)
        valid = True #binary parameter for whether or not we should keep the proposed geometry

        #if minimum distance is too small
        min_dist,max_dist = syst.get_min_max_distance(surf, ads)
        if min_dist < min_cutoff or max_dist>max_cutoff: #retranslate the ads in the plane
            new_coord = generate_random_positions.fragments_get_coordmatrix(surf, ads)
            valid = False
            too_close_index.append(i)
        else:
            new_coord =  generate_random_positions.fragments_get_coordmatrix(surf,ads)
            adsorbate.coord = new_coord
            dz = ads.dz
            dx = ads.dx+ads.dy*np.tan(30*np.pi/180) 
            dy = ads.dy
            adsorbate.z = dz*1.0e-10
            adsorbate.x = dx*1.0e-10
            adsorbate.y = dy*1.0e-10
            coordfile.write(str(adsorbate.x).replace('[','').replace(']','') + '   ' + str(adsorbate.y).replace('[','').replace(']','') + '   ' + str(adsorbate.z).replace('[','').replace(']','') + '\n')
            gamma = ads.gamma
            dz_array.append(dz)
            potential_E_J = V_pytorch(adsorbate, models,mpts) #Depends on the required inputs to the type of surrogate used!
            #potential_E_J = V3D(adsorbate,ads) 
            pot_E_eV = adsorbate.pot_E_J*kJ/1e3
            energyfile.write(str(pot_E_eV).replace('[','').replace(']','') + '\n')
            if pot_E_eV < -0.05: #report if there are negative energies.
                print("negative potential energy!" + str(pot_E_eV) + " eV. This indicates that we do not have the correct reference zero of energy.")

        if not valid:
            print("not valid geometry")
            points_not_valid +=1 
        else:
            dx_array.append(dx)
            dy_array.append(dy)
            gamma_array.append(gamma)
            potential_array.append(adsorbate.pot_E_J)
            for i,T in enumerate(T_array):
                integral[i] += P3D(adsorbate, T) 
                int_E_integral[i] += adsorbate.pot_E_J/(kB*T)*P3D(adsorbate, T)
                squared_int_E_integral[i] += adsorbate.pot_E_J**2.0/(kB*T)**2.0*P3D(adsorbate, T)
            answer = (ads.z_high-ads.z_low)*(ads.x_boundaries[1]-ads.x_boundaries[0])*(ads.y_boundaries[1]-ads.y_boundaries[0])*((1e-10)**3.0)/float(points_needed+1)*integral #units - meters3
            answer_old = answer
            points_needed_old = points_needed
            trans_kinetic_factor=(np.sqrt(2.0*np.pi*mu*kB*T_array))**3.0
            new_q_MC = answer*trans_kinetic_factor/(h**3.0) 
            if points_needed>29 and points_needed%5==0: #include a minimum of 30 points before thinking about convergence of the partition function
                if points_needed != 30:
                    conv_param_array = np.abs(new_q_MC-q_MC_5)/q_MC_5
                    conv_param=np.max(conv_param_array)
                    q_MC_5 = new_q_MC
                else:
                    q_MC_5 = new_q_MC
            points_needed +=1
            q_MC=new_q_MC
   
    f = open("output.txt", "a")
    f.write("Partition function covergence: " + str(conv_param) + "\n")
    f.write("Integration points: " + str(points_needed) + "\n")
    f.write("Points thrown away:" + str(points_not_valid) + "\n")
    f.close()
    adsorbate.points_needed = points_needed
    adsorbate.points_not_valid = points_not_valid
    adsorbate.potential_array = potential_array
    adsorbate.dz_array = dz_array
    adsorbate.dx_array = dx_array
    adsorbate.dy_array = dy_array
    #adsorbate.gamma_array = gamma_array

    adsorbate.q_MC = q_MC
    adsorbate.I1 = int_E_integral/integral
    adsorbate.I2 = squared_int_E_integral/integral
    return 

#######################################################################################################
def parse_input_file(filename, adsorbate):
    abs_file_path = str(filename)  

    input_file = open(abs_file_path, 'r')
    lines = input_file.readlines()
    input_file.close()

    error_name = True
    error_surface = True
    error_composition = True
    error_adsorbate_mass = True
    error_frequencies = True 
    error_zlow = True
    error_zhigh = True
    error_ucx = True
    error_ucy = True
    error_Tlow = True
    error_Thigh = True
    error_dT = True

    for line in lines:
        #Start by looking for the name
        if line.strip().startswith("name"):
            bits = line.split('=')
            name = bits[1].strip().replace("'","").replace('"','')
            adsorbate.name = name
            error_name = False
        #Now look for the surface
        if line.strip().startswith("surface"):
            bits = line.split('=')
            name = bits[1].strip().replace("'","").replace('"','')
            adsorbate.surface = name
            error_surface = False
        #Now look for the composition    
        elif line.strip().startswith("composition"):
            bits = line.split('=') 
            composition = bits[1].strip().replace("{","").replace("}","").split(',')
            adsorbate.composition = {}
            for pair in composition:
                element, number = pair.split(":")
                element = element.strip().replace("'","").replace('"','')
                number = int(number)
                adsorbate.composition[element]=number
            N_adsorbate_atoms = 0
            for element in adsorbate.composition:
                if element!='Pt':
                    N_adsorbate_atoms += adsorbate.composition[element]            
            error_composition = False
        #Now look for the adsorbate mass
        elif line.strip().startswith("adsorbate_mass"):
            bits = line.split('=') 
            adsorbate_mass_info = bits[1].strip().replace("[","").replace("]","").split(',')
            adsorbate_mass = float(adsorbate_mass_info[0])
            units = adsorbate_mass_info[1].strip().replace("'","").replace('"','')
            if units=='kg':
                adsorbate.mu = adsorbate_mass
                adsorbate.mu_units = units.strip()
                error_adsorbate_mass = False
            else:
                print("Adsorbate mass is missing proper units!\n Please use 'kg'")
                break 
        #Now look for the frequencies    
        elif line.strip().startswith("frequencies"):
            bits = line.split('=')
            freq_info = bits[1].strip().replace("[","").replace("]","").split(',')
            N_freq_computed = 3*N_adsorbate_atoms
            if len(freq_info)!=N_freq_computed+1:
                print("ERROR: The number of frequencies is not what was expected\n %d expected, but only %d received"%(N_freq_computed, len(freq_info)-1))
            units = freq_info[-1]   
            if units=='eV' or units!='cm-1':
                adsorbate.frequencies_units = units.strip()
                adsorbate.frequencies = []
                for i in range(len(freq_info)-1):
                    adsorbate.frequencies.append(float(freq_info[i]))
                error_frequencies = False
#                print(adsorbate.frequencies)
        #Now look for the z lower boundary relative to COM
        elif line.strip().startswith("z_low"):
            bits = line.split('=')
            zlow_info = bits[1].strip().replace("[","").replace("]","").split(',')
            zlow = float(zlow_info[0])
            units = zlow_info[1].strip().replace("'","").replace('"','')
            if units=='Angstrom' or units=='angstrom':
                adsorbate.z_low = zlow
                adsorbate.z_low_units = units.strip()
                error_zlow = False
            else:
                print("Adsorbate z lower boundary is missing proper units!\n Please use 'Angstrom'")
                break
        #Now look for the z higher boundary relative to COM
        elif line.strip().startswith("z_high"):
            bits = line.split('=')
            zhigh_info = bits[1].strip().replace("[","").replace("]","").split(',')
            zhigh = float(zhigh_info[0])
            units = zhigh_info[1].strip().replace("'","").replace('"','')
            if units=='Angstrom' or units=='angstrom':
                adsorbate.z_high = zhigh
                adsorbate.z_high_units = units.strip()
                error_zhigh = False
            else:
                print("Adsorbate z higher boundary is missing proper units!\n Please use 'Angstrom'")
                break
        #Now look for the uc_x parameter (width of 3x3 unit cell for a 111 surface)
        elif line.strip().startswith("uc_x"):
            bits = line.split('=')
            ucx_info = bits[1].strip().replace("[","").replace("]","").split(',')
            ucx = float(ucx_info[0])
            units = ucx_info[1].strip().replace("'","").replace('"','')
            if units=='Angstrom' or units=='angstrom':
                adsorbate.uc_x = ucx
                adsorbate.ucx_units = units.strip()
                error_ucx = False
            else:
                print("Unit cell width (x) is missing proper units!\n Please use 'Angstrom'")
                break
        #Now look for the uc_y parameter (right angle length of 3x3 unit cell for a 111 surface)
        elif line.strip().startswith("uc_y"):
            bits = line.split('=')
            ucy_info = bits[1].strip().replace("[","").replace("]","").split(',')
            ucy = float(ucy_info[0])
            units = ucy_info[1].strip().replace("'","").replace('"','')
            if units=='Angstrom' or units=='angstrom':
                adsorbate.uc_y = ucy
                adsorbate.ucy_units = units.strip()
                error_ucy = False
            else:
                print("Unit cell length (y) is missing proper units!\n Please use 'Angstrom'")
                break
        #Now look for the Temperature range
        elif line.strip().startswith("T_low"):
            bits = line.split('=')
            Tlow_info = bits[1].strip().replace("[","").replace("]","").split(',')
            Tlow = float(Tlow_info[0])
            units = Tlow_info[1].strip().replace("'","").replace('"','')
            if units == 'K':
                adsorbate.T_low = Tlow
                adsorbate.T_low_units = units.strip()
                error_Tlow = False
            else:
                print("Lower T limit is missing proper units!\n Please use 'K'")
                break
        elif line.strip().startswith("T_high"):
            bits = line.split('=')
            Thigh_info = bits[1].strip().replace("[","").replace("]","").split(',')
            Thigh = float(Thigh_info[0])
            units = Thigh_info[1].strip().replace("'","").replace('"','')
            if units == 'K':
                adsorbate.T_high = Thigh
                adsorbate.T_high_units = units.strip()
                error_Thigh = False
            else:
                print("Higher T limit is missing proper units!\n Please use 'K'")
                break
        elif line.strip().startswith("dT"):
            bits = line.split('=')
            dT_info = bits[1].strip().replace("[","").replace("]","").split(',')
            dT = float(dT_info[0])
            units = dT_info[1].strip().replace("'","").replace('"','')
            if units == 'K':
                adsorbate.dT = dT
                adsorbate.dT_units = units.strip()
                error_dT = False
            else:
                print("dT is missing proper units!\n Please use 'K'")
        elif line.strip().startswith("Q_acc"):
            bits = line.split('=')
            adsorbate.q_accuracy = float(bits[1].strip())
                
    if error_name or error_surface or error_composition or error_adsorbate_mass or error_frequencies or error_zlow or error_zhigh or error_ucx or error_ucy or error_Tlow or error_Thigh or error_dT:
        print("Input file is missing information: %s"%(filename))
    else:
        print("successfully parsed file %s"%(filename))
    
    return
