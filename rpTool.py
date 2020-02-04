#!/usr/bin/env python3

import libsbml
import sys
import logging

sys.path.insert(0, '/home/')
import rpSBML


#TODO: use rpSBML annottions function instead of manual
## Extract the reaction SMILES from an SBML, query selenzyme and write the results back to the SBML
#
# NOTE: all the scores are normalised by their maximal and minimal, and normalised to be higher is better
#
def calculateGlobalScore(rpsbml,
                         weight_rp_steps,
                         weight_selenzyme,
                         weight_fba,
                         weight_thermo,
                         max_rp_steps,
                         thermo_ceil=8901.2,
                         thermo_floor=-7570.2,
                         fba_ceil=999999.0,
                         fba_floor=0.0,
                         pathway_id='rp_pathway',
                         objective_id='obj_rpFBA_frac',
                         thermo_id='dfG_prime_m'):
    groups = rpsbml.model.getPlugin('groups')
    fbc = rpsbml.model.getPlugin('fbc')
    rp_pathway = groups.getGroup(pathway_id)
    members = rp_pathway.getListOfMembers()
    all_rule_score = 0.0
    top_selenzyme = 0.0
    all_norm_thermo = 0.0
    #Loop through all the reactions
    for member in members:
        reaction = rpsbml.model.getReaction(member.getIdRef())
        annot = reaction.getAnnotation()
        brsynth_dict = rpsbml.readBRSYNTHAnnotation(annot)
        ####### selenzyme ############
        #higher is better
        try:
            #sum of mean of top selenzyme score
            selen_score = brsynth_dict['selenzyme'][sorted(brsynth_dict['selenzyme'], key=lambda kv: kv[1])[0]]
            top_selenzyme += selen_score
            rpsbml.addUpdateBRSynth(reaction, 'norm_selenzyme', selen_score/100.0)
        except (IndexError, TypeError) as e:
            logging.warning('We are missing a selenzyme values')
        ####### Thermo ############
        #lower is better
        #WARNING: we will only take the dfG_prime_m value
        norm_thermo = 0.0
        try:
            if thermo_ceil>=brsynth_dict[thermo_id]['value']>=thermo_floor:
                #min-max feature scaling
                norm_thermo = (brsynth_dict[thermo_id]['value']-thermo_floor)/(thermo_ceil-thermo_floor)
            elif brsynth_dict[thermo_id]['value']<thermo_floor:
                norm_thermo = 0.0
            elif brsynth_dict[thermo_id]['value']>thermo_ceil:
                norm_thermo = 1.0
        except (KeyError, TypeError) as e:
            norm_thermo = 1.0
        norm_thermo = 1.0-norm_thermo
        all_norm_thermo += norm_thermo
        rpsbml.addUpdateBRSynth(reaction, 'norm_dfG_prime_m', norm_thermo)
        ####### FBA ##############
        #higher is better
        #return all the FBA values
        norm_fba = 0.0
        for brs_key in brsynth_dict:
            #if brs_key[:4]=='fba_':
            if brs_key==obj_name:
                #min-max feature scaling
                norm_fba = (round(float(brsynth_dict[brs_key]['value']), 4)-fba_floor)/(fba_ceil-fba_floor)
                rpsbml.addUpdateBRSynth(reaction, 'norm_'+str(brs_key), norm_fba)
    ##############################
    ####### selenzyme ############
    ##############################
    #higher is better
    #NOTE: that missing selenzyme value will be considered 0.0 since we divide by the number of members
    norm_selenzyme = (top_selenzyme/float(len(members)))/100.0
    rpsbml.addUpdateBRSynth(rp_pathway, 'norm_selenzyme', norm_selenzyme)
    ##############################
    ##### target FBA value #######
    ##############################
    #higher is better
    #loop through all the different objectives and normalise the values
    #find the objective
    obj_objective = None
    for objective in fbc.getListOfObjectives():
        if objective.getId()==objective_id:
            obj_objective = objective
            break
    if obj_objective:
        #for obj in fbc.getListOfObjectives():
        brsynth_dict = rpsbml.readBRSYNTHAnnotation(obj_objective.getAnnotation())
        try:
            #min-max feature scaling for dfG_prime_m
            if fba_ceil>=float(brsynth_dict['flux_value']>=fba_floor:
                norm_fba = (round(float(brsynth_dict['flux_value']), 4)-fba_floor)/(fba_ceil-fba_floor)
            elif float(brsynth_dict['flux_value'])<fba_floor:
                norm_fba = 0.0
            elif float(brsynth_dict['flux_value'])>fba_ceil:
                norm_fba = 1.0
        except (KeyError, TypeError) as e:
            logging.warning('Could not retreive flux value: '+str(objective_id))
            norm_fba = 0.0
        rpsbml.addUpdateBRSynth(obj_objective, 'norm_flux_value', norm_fba)
        rpsbml.addUpdateBRSynth(rp_pathway, 'norm_'+obj_objective.getId(), norm_fba)
        #update the flux obj
        for flux_obj in obj_objective.getListOfAllElements():
            #min-max feature scaling
            try:
                norm_fba = (round(float(), 4)-fba_floor)/(fba_ceil-fba_floor)
            except (KeyError, TypeError) as e:
                norm_fba = 0.0
            rpsbml.addUpdateBRSynth(flux_obj, 'norm_flux_value', norm_fba)
    else:
        logging.warning('Could not find objective: '+str(objective_id))
        norm_fba = 0.0
    ##############################
    #### group thermo ############
    ##############################
    #lower is better
    #loop through all the reactions and retreive the thermo score for the reactions directly and sum up
    '''if you want to use the rpThermo pathway value
    brsynth_dict = rpsbml.readBRSYNTHAnnotation(rp_pathway.getAnnotation())
    norm_thermo = 0.0
    try:
        if thermo_ceil>=brsynth_dict['dfG_prime_m']['value']>=thermo_floor:
            #min-max feature scaling
            norm_thermo = (brsynth_dict['dfG_prime_m']['value']-thermo_floor)/(thermo_ceil-thermo_floor)
        elif brsynth_dict['dfG_prime_m']['value']<thermo_floor:
            norm_thermo = 0.0
        elif brsynth_dict['dfG_prime_m']['value']>thermo_ceil:
            norm_thermo = 1.0
    except (KeyError, TypeError) as e:
        norm_thermo = 1.0
    norm_thermo = 1.0-norm_thermo
    rpsbml.addUpdateBRSynth(rp_pathway, 'norm_dfG_prime_m', norm_thermo)
    '''
    #if you want the mean of each reaction normalisation
    rpsbml.addUpdateBRSynth(rp_pathway, 'norm_dfG_prime_m', all_norm_thermo/len(members))
    ############################
    ##### length of members ####
    ############################
    #lower is better
    if len(members)>max_rp_steps:
        logging.warning('There are more steps than specified')
        norm_steps = 1.0
    else:
        norm_steps = (float(len(members))-1.0)/(float(max_rp_steps)-1.0)
    norm_steps = 1.0-norm_steps
    rpsbml.addUpdateBRSynth(rp_pathway, 'norm_steps', norm_steps)
    ############################
    ##### global score #########
    ############################
    globalScore = (norm_selenzyme*weight_selenzyme+norm_steps*weight_rp_steps+norm_fba*weight_fba+norm_thermo*weight_thermo)/4.0
    rpsbml.addUpdateBRSynth(rp_pathway, 'global_score', globalScore)
    return globalScore
