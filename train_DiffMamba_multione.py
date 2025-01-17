from improved_diffusion import dist_util, logger
from improved_diffusion.resample import create_named_schedule_sampler
from improved_diffusion.script_util import (
    model_and_diffusion_defaults,
    create_model_and_diffusion,
    create_full_size_model_and_diffusion,
)
from improved_diffusion.train_util import TrainLoop
import warnings
warnings.filterwarnings('ignore')

import os
import torch
import torchvision.transforms as transforms

from data_loader_Cmask import LoadTestDataMulti, LoadTrainDataPatchMulti
from time import gmtime, strftime
current_time = strftime("%m%d_%H_%M", gmtime())
current_day = strftime("%m%d", gmtime())

############################
# model_path = "/home/zhenlin/DiffMamba/log/v5_cmask4_Tssm_conv_lnorm/model_597000.pt"
os.environ["CUDA_VISIBLE_DEVICES"] = "2"
logdir = "/home/zhenlin/DiffMamba/log/Multi_fromscratch/v5_cmask4/"

############################
import wandb

def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


wandb.init(project="DiffMamba ST Multi", name = "v5 cmask4 fromscratch")
wandb.config = {"epochs": 500*1194, "batch_size": 12}

max_iter=119400*5
start_log_iter=1194*100
start_test_iter=1194*100
lr = 2e-5
lr_anneal_steps=119400*5

def main():
    logger.configure(dir=logdir)
    arg_dict = model_and_diffusion_defaults()
    arg_dict["image_size"]=128

    print(arg_dict)
    model, diffusion = create_full_size_model_and_diffusion(**arg_dict)
    logger.log("creating model and diffusion...")
    print('model parameters:', count_parameters(model))
    logger.log(f"Model parameters: {count_parameters(model)}")
    logger.log(arg_dict)
    logger.log("Acc=04, ACS =10, full size")
    
    # model.load_state_dict(
    #     dist_util.load_state_dict(model_path, map_location="cpu")
    # )
    logger.log(f"using GPU{os.environ['CUDA_VISIBLE_DEVICES']}")
    logger.log("model details: adding tem ssm block to ds attention, add conv1d and layer norm mlp, expand tem dim")
    logger.log(f'max iter: {max_iter}, start log iter: {start_log_iter}, start test iter: {start_test_iter}')
    logger.log(f"lr: {lr}, lr_anneal_steps: {lr_anneal_steps}")
    logger.log(f"import from ssm v5 Tssm conv, train from scratch")
    model.to(dist_util.dev())
    schedule_sampler = create_named_schedule_sampler("uniform", diffusion)

    tsfm = transforms.Compose([
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomVerticalFlip(p=0.5),
    ])
    dataset = LoadTrainDataPatchMulti(4,'sax', tsfm)
    test_dataset = LoadTestDataMulti(4, 'sax')
    print(len(dataset))
    torch.set_num_threads(8)

    TrainLoop(
            model=model,
            diffusion=diffusion,
            data=dataset,
            batch_size=12,
            microbatch=-1,
            lr=lr,
            ema_rate="0.9999",
            log_interval=1194,
            save_interval=1194*10,
            resume_checkpoint="",
            use_fp16=False,
            fp16_scale_growth=1e-3,
            schedule_sampler=schedule_sampler,
            weight_decay=0.0,
            lr_anneal_steps=lr_anneal_steps,
            start_training_step = 0,
            clip_denoised=False,
            logger=logger,
            logdir = logdir,
            val_dataset=test_dataset,
            run_with_test=True,
        ).run_loop(max_iter=max_iter, start_log_iter=start_log_iter, start_test_iter=start_test_iter)

if __name__ == "__main__":
    main()
    